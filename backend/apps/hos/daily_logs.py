"""
Daily log generation and 24-hour segment splitting logic.
Generates FMCSA-compliant 24-hour daily logs, structured remarks, and SVG grid metadata.
Pure representation layer without recalculating HOS decisions.
"""

from datetime import datetime, date, time, timedelta
from typing import List, Dict, Optional
from collections import defaultdict
import logging

from .enums import DutyStatus
from .models import DutySegment, DailyLog, DailyTotals, Remark, DailySchedule

logger = logging.getLogger(__name__)


def map_event_type(reason: Optional[str], status: DutyStatus) -> Optional[str]:
    """Extracts operational event type from reason string and duty status."""
    if not reason:
        return None
    r_lower = reason.lower()
    if "pickup" in r_lower:
        return "PICKUP"
    if "dropoff" in r_lower:
        return "DROPOFF"
    if "fuel" in r_lower:
        return "FUEL"
    if "break" in r_lower:
        return "BREAK"
    if "reset" in r_lower or "sleeper" in r_lower or "rest" in r_lower or status == DutyStatus.SLEEPER_BERTH:
        return "REST"
    return None


def generate_remarks_for_segments(segments: List[DutySegment]) -> List[Remark]:
    """Generates structured remarks for status changes and planned events."""
    remarks: List[Remark] = []

    for seg in segments:
        time_str = seg.start.strftime("%H:%M")
        desc = seg.reason

        if not desc:
            if seg.status == DutyStatus.DRIVING:
                desc = "Started driving"
            elif seg.status == DutyStatus.OFF_DUTY:
                desc = "Off duty"
            elif seg.status == DutyStatus.SLEEPER_BERTH:
                desc = "Entered sleeper berth"
            elif seg.status == DutyStatus.ON_DUTY_NOT_DRIVING:
                desc = "On duty (not driving)"

        ev_type = seg.event_type or map_event_type(seg.reason, seg.status)

        remarks.append(Remark(
            time=time_str,
            location=seg.location,
            description=desc,
            event_type=ev_type,
            coordinate=seg.coordinate,
        ))

    return remarks


class DailyLogBuilder:
    """
    Pure domain builder that transforms a sequence of scheduled TripSchedule segments
    into FMCSA 24-hour Daily Logs.
    
    Guarantees:
    - Exactly 1,440 minutes (24.0 hours) per calendar day.
    - Zero gaps between 00:00 and 24:00.
    - Zero overlapping segments.
    - Clean midnight splitting for segments that cross 00:00.
    - Accurate startMinute and endMinute offsets [0, 1440].
    - Server-side calculated minute and hour totals.
    """

    def build_logs(self, scheduled_segments: List[DutySegment]) -> List[DailyLog]:
        if not scheduled_segments:
            logger.debug("[DailyLogBuilder.build_logs] Empty scheduled_segments list received")
            return []

        logger.info("[DailyLogBuilder.build_logs] Building daily logs for %d scheduled segments", len(scheduled_segments))

        # Find earliest start and latest end
        trip_start = scheduled_segments[0].start
        trip_end = scheduled_segments[-1].end

        start_date = trip_start.date()
        end_date = trip_end.date()

        tz = trip_start.tzinfo

        # 1. Prepend OFF_DUTY from midnight of start_date to trip_start
        all_segments: List[DutySegment] = []
        day_start_midnight = datetime.combine(start_date, time.min, tzinfo=tz)

        if trip_start > day_start_midnight:
            pre_mins = int((trip_start - day_start_midnight).total_seconds() / 60)
            if pre_mins > 0:
                all_segments.append(DutySegment(
                    status=DutyStatus.OFF_DUTY,
                    start=day_start_midnight,
                    end=trip_start,
                    duration_minutes=pre_mins,
                    location=scheduled_segments[0].location,
                    miles=0.0,
                    reason="Off duty (pre-trip)",
                    coordinate=scheduled_segments[0].coordinate,
                    event_type=None,
                ))

        all_segments.extend(scheduled_segments)

        # 2. Append OFF_DUTY from trip_end to midnight of end_date
        day_end_midnight = datetime.combine(end_date + timedelta(days=1), time.min, tzinfo=tz)
        if trip_end < day_end_midnight:
            post_mins = int((day_end_midnight - trip_end).total_seconds() / 60)
            if post_mins > 0:
                all_segments.append(DutySegment(
                    status=DutyStatus.OFF_DUTY,
                    start=trip_end,
                    end=day_end_midnight,
                    duration_minutes=post_mins,
                    location=scheduled_segments[-1].location,
                    miles=0.0,
                    reason="Off duty (post-trip)",
                    coordinate=scheduled_segments[-1].coordinate,
                    event_type=None,
                ))

        # 3. Split any segment that crosses midnight
        day_split_segments: List[DutySegment] = []
        for seg in all_segments:
            curr_start = seg.start
            curr_end = seg.end
            total_seg_mins = seg.duration_minutes
            total_seg_miles = seg.miles
            ev_type = seg.event_type or map_event_type(seg.reason, seg.status)

            while curr_start.date() < curr_end.date():
                next_midnight = datetime.combine(curr_start.date() + timedelta(days=1), time.min, tzinfo=curr_start.tzinfo)
                chunk_mins = int((next_midnight - curr_start).total_seconds() / 60)

                chunk_miles = 0.0
                if total_seg_mins > 0 and total_seg_miles > 0:
                    chunk_miles = round(total_seg_miles * (chunk_mins / total_seg_mins), 2)

                day_split_segments.append(DutySegment(
                    status=seg.status,
                    start=curr_start,
                    end=next_midnight,
                    duration_minutes=chunk_mins,
                    location=seg.location,
                    miles=chunk_miles,
                    reason=seg.reason,
                    coordinate=seg.coordinate,
                    leg=seg.leg,
                    event_type=ev_type,
                ))

                curr_start = next_midnight
                total_seg_miles = max(0.0, total_seg_miles - chunk_miles)
                total_seg_mins = max(0, total_seg_mins - chunk_mins)

            # Remaining piece within same calendar day
            rem_mins = int((curr_end - curr_start).total_seconds() / 60)
            if rem_mins > 0:
                day_split_segments.append(DutySegment(
                    status=seg.status,
                    start=curr_start,
                    end=curr_end,
                    duration_minutes=rem_mins,
                    location=seg.location,
                    miles=round(total_seg_miles, 2),
                    reason=seg.reason,
                    coordinate=seg.coordinate,
                    leg=seg.leg,
                    event_type=ev_type,
                ))

        # 4. Group segments by calendar date
        days_map: Dict[str, List[DutySegment]] = defaultdict(list)
        for seg in day_split_segments:
            date_str = seg.start.date().isoformat()
            days_map[date_str].append(seg)

        # 5. Build and validate DailyLog for each day
        daily_logs: List[DailyLog] = []
        sorted_dates = sorted(days_map.keys())

        for idx, date_str in enumerate(sorted_dates):
            segs = days_map[date_str]
            d_obj = datetime.strptime(date_str, "%Y-%m-%d").date()
            day_midnight = datetime.combine(d_obj, time.min, tzinfo=tz)

            # Calculate minute offsets from midnight for each segment
            processed_segs: List[DutySegment] = []
            off_duty_m = 0
            sleeper_m = 0
            driving_m = 0
            on_duty_m = 0
            day_miles = 0.0

            for s in segs:
                start_m = int((s.start - day_midnight).total_seconds() / 60)
                end_m = int((s.end - day_midnight).total_seconds() / 60)
                dur_m = end_m - start_m

                s_copy = DutySegment(
                    status=s.status,
                    start=s.start,
                    end=s.end,
                    duration_minutes=dur_m,
                    location=s.location,
                    miles=s.miles,
                    reason=s.reason,
                    coordinate=s.coordinate,
                    leg=s.leg,
                    start_minute=start_m,
                    end_minute=end_m,
                    event_type=s.event_type or map_event_type(s.reason, s.status),
                )
                processed_segs.append(s_copy)

                day_miles += s.miles
                if s.status == DutyStatus.OFF_DUTY:
                    off_duty_m += dur_m
                elif s.status == DutyStatus.SLEEPER_BERTH:
                    sleeper_m += dur_m
                elif s.status == DutyStatus.DRIVING:
                    driving_m += dur_m
                elif s.status == DutyStatus.ON_DUTY_NOT_DRIVING:
                    on_duty_m += dur_m

            # 6. INVARIANT CHECKS FOR 24-HOUR FMCSA LOG
            if not processed_segs:
                raise ValueError(f"Daily log for date {date_str} has no segments.")

            if processed_segs[0].start_minute != 0:
                raise ValueError(
                    f"Daily log for {date_str} does not start at minute 0 (starts at {processed_segs[0].start_minute})."
                )

            if processed_segs[-1].end_minute != 1440:
                raise ValueError(
                    f"Daily log for {date_str} does not end at minute 1440 (ends at {processed_segs[-1].end_minute})."
                )

            total_seg_minutes = 0
            for i, p_seg in enumerate(processed_segs):
                if p_seg.duration_minutes <= 0:
                    raise ValueError(f"Segment {i} on {date_str} has non-positive duration: {p_seg.duration_minutes}m.")
                if i > 0:
                    prev = processed_segs[i - 1]
                    if p_seg.start_minute != prev.end_minute:
                        raise ValueError(
                            f"Gap or overlap on {date_str} between segment {i-1} (end {prev.end_minute}) and segment {i} (start {p_seg.start_minute})."
                        )
                total_seg_minutes += p_seg.duration_minutes

            if total_seg_minutes != 1440:
                raise ValueError(
                    f"Daily log for {date_str} total minutes is {total_seg_minutes}, expected exactly 1440 (24.0 hours)."
                )

            totals = DailyTotals(
                off_duty=round(off_duty_m / 60.0, 2),
                sleeper_berth=round(sleeper_m / 60.0, 2),
                driving=round(driving_m / 60.0, 2),
                on_duty_not_driving=round(on_duty_m / 60.0, 2),
                off_duty_minutes=off_duty_m,
                sleeper_berth_minutes=sleeper_m,
                driving_minutes=driving_m,
                on_duty_not_driving_minutes=on_duty_m,
            )

            if totals.total_minutes != 1440:
                raise ValueError(
                    f"Daily totals on {date_str} sum to {totals.total_minutes}m, expected 1440m."
                )

            remarks = generate_remarks_for_segments(processed_segs)

            logger.debug(
                "[DailyLogBuilder] Day %d (%s): %d segments, driving=%.1fh, on_duty=%.1fh, off_duty=%.1fh, sleeper=%.1fh (total=1440m)",
                idx + 1, date_str, len(processed_segs), totals.driving, totals.on_duty_not_driving, totals.off_duty, totals.sleeper_berth
            )

            daily_logs.append(DailyLog(
                date=date_str,
                day_number=idx + 1,
                total_miles=round(day_miles, 2),
                segments=processed_segs,
                remarks=remarks,
                totals=totals,
            ))

        logger.info("[DailyLogBuilder.build_logs] Generated %d 24-hour daily logs successfully", len(daily_logs))
        return daily_logs


def split_segments_by_calendar_day(
    scheduled_segments: List[DutySegment],
    default_off_duty_location: str = "Origin",
) -> List[DailyLog]:
    """Compatibility function delegating to DailyLogBuilder."""
    builder = DailyLogBuilder()
    return builder.build_logs(scheduled_segments)


def build_daily_schedules(daily_logs: List[DailyLog]) -> List[DailySchedule]:
    """Builds high-level DailySchedule objects from daily logs."""
    schedules: List[DailySchedule] = []
    for log in daily_logs:
        schedules.append(DailySchedule(
            date=log.date,
            segments=log.segments,
            total_driving_hours=log.totals.driving,
            total_on_duty_hours=round(log.totals.driving + log.totals.on_duty_not_driving, 2),
            total_off_duty_hours=log.totals.off_duty,
            total_sleeper_hours=log.totals.sleeper_berth,
            total_hours=round(log.totals.total_hours, 2),
        ))
    return schedules
