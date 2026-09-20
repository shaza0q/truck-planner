import { DutySegment, DutyStatus } from '../../types/hos';

export const STATUS_ROW_Y: Record<DutyStatus, number> = {
  OFF_DUTY: 35,
  SLEEPER_BERTH: 95,
  DRIVING: 155,
  ON_DUTY_NOT_DRIVING: 215,
};

export const STATUS_ROW_HEIGHT = 60;
export const GRAPH_TOTAL_MINUTES = 1440;
export const GRAPH_HEIGHT = 270;

export interface PathResult {
  pathD: string;
  segmentsWithCoords: Array<{
    segment: DutySegment;
    xStart: number;
    xEnd: number;
    y: number;
    color: string;
  }>;
}

/**
 * Builds the continuous stepped SVG path for a 24-hour daily log.
 * Moves horizontally during a status, and steps vertically at the exact status transition minute.
 */
export function buildDailyLogPath(segments: DutySegment[]): PathResult {
  if (!segments || segments.length === 0) {
    return { pathD: '', segmentsWithCoords: [] };
  }

  const commands: string[] = [];
  const segmentsWithCoords: PathResult['segmentsWithCoords'] = [];

  let lastY: number | null = null;

  segments.forEach((seg, index) => {
    const startM = seg.startMinute ?? 0;
    const endM = seg.endMinute ?? startM + seg.durationMinutes;
    const currentY = STATUS_ROW_Y[seg.status] ?? STATUS_ROW_Y.OFF_DUTY;

    if (index === 0) {
      commands.push(`M ${startM} ${currentY}`);
    } else if (lastY !== null && lastY !== currentY) {
      // Step vertically at the boundary minute
      commands.push(`V ${currentY}`);
    }

    // Move horizontally across the segment duration
    commands.push(`H ${endM}`);
    lastY = currentY;

    let color = '#B8BCB7';
    switch (seg.status) {
      case 'DRIVING':
        color = '#245C4A'; // Forest Green
        break;
      case 'ON_DUTY_NOT_DRIVING':
        color = '#A66A21'; // Muted Amber
        break;
      case 'SLEEPER_BERTH':
        color = '#60788A'; // Muted Blue / Slate
        break;
      case 'OFF_DUTY':
        color = '#B8BCB7'; // Neutral Muted
        break;
    }

    segmentsWithCoords.push({
      segment: seg,
      xStart: startM,
      xEnd: endM,
      y: currentY,
      color,
    });
  });

  return {
    pathD: commands.join(' '),
    segmentsWithCoords,
  };
}

/**
 * Formats minute count into "Xh Ym" string (e.g. 480 -> "8h 00m", 90 -> "1h 30m").
 */
export function formatMinutesToHM(minutes: number): string {
  const h = Math.floor(minutes / 60);
  const m = Math.round(minutes % 60);
  if (m === 0) return `${h}h 00m`;
  return `${h}h ${m < 10 ? '0' : ''}${m}m`;
}

/**
 * Formats minute offset from midnight (0-1440) into 12-hour AM/PM string.
 */
export function formatMinuteToTimeStr(minute: number): string {
  const normMin = Math.min(1440, Math.max(0, minute));
  const totalH = Math.floor(normMin / 60);
  const m = normMin % 60;
  const mStr = m < 10 ? `0${m}` : `${m}`;

  if (totalH === 0 || totalH === 24) return `12:${mStr} AM`;
  if (totalH === 12) return `12:${mStr} PM`;
  if (totalH < 12) return `${totalH}:${mStr} AM`;
  return `${totalH - 12}:${mStr} PM`;
}
