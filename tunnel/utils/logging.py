"""
Logging utilities for tunnel service
"""

import logging
import sys
from datetime import datetime
from typing import Optional


class ColoredFormatter(logging.Formatter):
    """Colored log formatter"""
    
    COLORS = {
        'DEBUG': '\033[36m',     # Cyan
        'INFO': '\033[32m',      # Green
        'WARNING': '\033[33m',   # Yellow
        'ERROR': '\033[31m',     # Red
        'CRITICAL': '\033[35m',  # Magenta
    }
    RESET = '\033[0m'
    
    def format(self, record):
        # Add color to levelname
        levelname = record.levelname
        if levelname in self.COLORS:
            record.levelname = f"{self.COLORS[levelname]}{levelname}{self.RESET}"
        
        return super().format(record)


def _level_from_env(default: int = logging.INFO) -> int:
    """Read TUNNEL_LOG_LEVEL (DEBUG/INFO/WARNING/ERROR), fallback to default"""
    import os
    return getattr(logging, os.getenv("TUNNEL_LOG_LEVEL", "").upper(), default)


def setup_logger(name: str, level: Optional[int] = None,
                 colored: bool = True) -> logging.Logger:
    """Setup logger with colored output (level from TUNNEL_LOG_LEVEL env)"""
    if level is None:
        level = _level_from_env()
    logger = logging.getLogger(name)
    logger.setLevel(level)
    
    # Remove existing handlers
    logger.handlers = []
    
    # Console handler
    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(level)
    
    # Formatter
    fmt = '%(asctime)s [%(levelname)s] %(name)s: %(message)s'
    date_fmt = '%H:%M:%S'
    
    if colored and sys.stdout.isatty():
        formatter = ColoredFormatter(fmt, date_fmt)
    else:
        formatter = logging.Formatter(fmt, date_fmt)
    
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    
    return logger


# Loggers
server_logger = setup_logger('tunnel.server')
client_logger = setup_logger('tunnel.client')
auth_logger = setup_logger('tunnel.auth')
proxy_logger = setup_logger('tunnel.proxy')
