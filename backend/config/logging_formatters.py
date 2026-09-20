"""
ANSI Colored Log Formatter for Django console output.
Provides vibrant, distinguishable colors for DEBUG, INFO, WARNING, ERROR, and CRITICAL.
"""

import logging
from typing import Optional


class ColoredFormatter(logging.Formatter):
    """
    Custom logging formatter that injects ANSI color codes
    based on the log record's level.
    """

    # ANSI Escape Codes
    RESET = "\033[0m"
    BOLD = "\033[1m"
    DIM = "\033[2m"

    # Foreground Colors
    GRAY = "\033[90m"
    CYAN = "\033[36m"
    GREEN = "\033[32m"
    BRIGHT_GREEN = "\033[92;1m"
    YELLOW = "\033[33m"
    BRIGHT_YELLOW = "\033[93;1m"
    RED = "\033[31m"
    BRIGHT_RED = "\033[91;1m"
    MAGENTA = "\033[35m"
    BRIGHT_MAGENTA = "\033[95m"
    WHITE_ON_RED = "\033[41;97;1m"

    # Level color mapping
    LEVEL_COLORS = {
        logging.DEBUG: CYAN,
        logging.INFO: BRIGHT_GREEN,
        logging.WARNING: BRIGHT_YELLOW,
        logging.ERROR: BRIGHT_RED,
        logging.CRITICAL: WHITE_ON_RED,
    }

    # Level badge mapping
    LEVEL_BADGES = {
        logging.DEBUG: "[DEBUG]  ",
        logging.INFO: "[INFO]   ",
        logging.WARNING: "[WARNING]",
        logging.ERROR: "[ERROR]  ",
        logging.CRITICAL: "[FATAL]  ",
    }

    def __init__(self, fmt: Optional[str] = None, datefmt: str = "%Y-%m-%d %H:%M:%S"):
        super().__init__(fmt=fmt, datefmt=datefmt)

    def format(self, record: logging.LogRecord) -> str:
        # Format the timestamp
        record.asctime = self.formatTime(record, self.datefmt)
        
        # Determine colors for this log level
        level_color = self.LEVEL_COLORS.get(record.levelno, self.RESET)
        badge = self.LEVEL_BADGES.get(record.levelno, f"[{record.levelname}]")
        
        # Color components
        time_part = f"{self.GRAY}[{record.asctime}]{self.RESET}"
        level_part = f"{level_color}{badge}{self.RESET}"
        name_part = f"{self.MAGENTA}[{record.name}]{self.RESET}"
        
        # Message color styling
        msg_color = self.RESET
        if record.levelno == logging.DEBUG:
            msg_color = self.DIM
        elif record.levelno == logging.WARNING:
            msg_color = self.YELLOW
        elif record.levelno in (logging.ERROR, logging.CRITICAL):
            msg_color = self.RED

        formatted_msg = f"{msg_color}{record.getMessage()}{self.RESET}"

        result = f"{time_part} {level_part} {name_part} {formatted_msg}"

        # If there is exception info or stack trace, append it with red highlight
        if record.exc_info:
            if not record.exc_text:
                record.exc_text = self.formatException(record.exc_info)
        if record.exc_text:
            result += f"\n{self.BRIGHT_RED}{record.exc_text}{self.RESET}"
        if record.stack_info:
            result += f"\n{self.GRAY}{self.formatStack(record.stack_info)}{self.RESET}"

        return result
