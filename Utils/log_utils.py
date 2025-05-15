import os
import sys
import logging
import datetime
from typing import Optional, Union, Literal

# Define log levels for easy reference
LOG_LEVEL_DEBUG = logging.DEBUG
LOG_LEVEL_INFO = logging.INFO
LOG_LEVEL_WARNING = logging.WARNING
LOG_LEVEL_ERROR = logging.ERROR
LOG_LEVEL_CRITICAL = logging.CRITICAL

# Define custom debug levels
DEBUG_L1 = 1  # Basic debug info (important debug messages)
DEBUG_L2 = 2  # Medium verbosity (more detailed information)
DEBUG_L3 = 3  # High verbosity (everything, including repetitive updates)

# Debug level usage guidelines:
# Level 1 (DEBUG_L1): Overview/summary logging. High-level application state changes,
#                     initialization successes, key operations completed successfully.
#                     This level should provide an overall picture of what's happening
#                     without too much detail.
#
# Level 2 (DEBUG_L2): Descriptive logging. Detailed operation information, object
#                     creation/modification, configuration details, parameters used.
#                     This level should provide enough context to understand what's
#                     happening in each component.
#
# Level 3 (DEBUG_L3): Reserved for frequently repeating operations, such as
#                     per-frame updates, drone movements, sensor readings, etc.
#                     This level will generate high volume logs and should only be
#                     enabled for detailed debugging of specific issues.

# ANSI color codes for colored output
COLORS = {
    'RESET': '\033[0m',
    'BLACK': '\033[30m',
    'RED': '\033[31m',
    'GREEN': '\033[32m',
    'YELLOW': '\033[33m',
    'BLUE': '\033[34m',
    'MAGENTA': '\033[35m',
    'CYAN': '\033[36m',
    'WHITE': '\033[37m',
    'BOLD': '\033[1m',
    'UNDERLINE': '\033[4m',
}

class ColoredFormatter(logging.Formatter):
    """Custom formatter that adds colors to log messages based on their level."""
    
    # Map log levels to colors
    LEVEL_COLORS = {
        logging.DEBUG: COLORS['BLUE'],
        logging.INFO: COLORS['GREEN'],
        logging.WARNING: COLORS['YELLOW'],
        logging.ERROR: COLORS['RED'],
        logging.CRITICAL: COLORS['BOLD'] + COLORS['RED'],
    }
    
    def format(self, record):
        # Add color to the levelname
        if hasattr(record, 'levelno') and record.levelno in self.LEVEL_COLORS:
            color = self.LEVEL_COLORS[record.levelno]
            record.levelname = f"{color}{record.levelname}{COLORS['RESET']}"
        
        return super().format(record)

class Logger:
    """
    Centralized logging utility that supports both console and file logging.
    Implements the Singleton pattern for consistent logging across the application.
    """
    _instance = None
    
    @classmethod
    def get_instance(cls):
        """Get or create the singleton Logger instance."""
        if cls._instance is None:
            cls._instance = Logger()
        return cls._instance
    
    def __init__(self):
        """Initialize the Logger instance."""
        # Ensure only one instance is created
        if Logger._instance is not None:
            raise Exception("Logger already exists! Use Logger.get_instance() to get the singleton instance.")
        
        # Initialize the root logger
        self.logger = logging.getLogger('drone_sim')
        self.logger.setLevel(logging.INFO)  # Default level
        
        # Default log format
        self.formatter = logging.Formatter(
            '%(asctime)s [%(levelname)s] %(name)s: %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        
        # Colored formatter for console
        self.colored_formatter = ColoredFormatter(
            '%(asctime)s [%(levelname)s] %(name)s: %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        
        # Console handler (always available)
        self.console_handler = logging.StreamHandler(sys.stdout)
        self.console_handler.setFormatter(self.colored_formatter)
        self.console_handler.setLevel(logging.INFO)
        self.logger.addHandler(self.console_handler)
        
        # File handler (added when configure_file_logging is called)
        self.file_handler = None
        self.log_directory = "logs"
        
        # Track if verbose mode is enabled
        self.verbose = False
        
        # Track debug level (1-3)
        self.current_debug_level = DEBUG_L1
        
        # Track if colored output is enabled
        self.colored_output = True
        
        # Set as instance
        Logger._instance = self
    
    def configure(self, verbose: bool = False, console_level: int = logging.INFO, 
                 log_directory: Optional[str] = None, debug_level: int = DEBUG_L1,
                 colored_output: bool = True):
        """
        Configure the logger settings.
        
        Args:
            verbose: Whether verbose logging is enabled
            console_level: Minimum level for console logging
            log_directory: Directory where log files should be stored
            debug_level: Debug verbosity level (1-3)
            colored_output: Whether to use colored output in console
        """
        self.verbose = verbose
        self.current_debug_level = debug_level
        self.colored_output = colored_output
        
        # Update console handler level
        min_level = logging.DEBUG if verbose else console_level
        self.console_handler.setLevel(min_level)
        self.logger.setLevel(min_level)
        
        # Update log directory if provided
        if log_directory:
            self.log_directory = log_directory
        
        # Update console formatter based on color preference
        if colored_output:
            self.console_handler.setFormatter(self.colored_formatter)
        else:
            self.console_handler.setFormatter(self.formatter)
        
        # Log the configuration
        self.info("Logger", f"Logger configured: verbose={verbose}, level={min_level}, debug_level={debug_level}, colored={colored_output}")
    
    def configure_file_logging(self, enabled: bool = True,
                              level: int = logging.DEBUG,
                              filename: Optional[str] = None):
        """
        Configure file logging.
        
        Args:
            enabled: Whether file logging should be enabled
            level: Minimum level for file logging
            filename: Specific filename to use (defaults to current datetime)
        """
        # Remove existing file handler if present
        if self.file_handler:
            self.logger.removeHandler(self.file_handler)
            self.file_handler = None
        
        if not enabled:
            self.info("Logger", "File logging disabled")
            return
        
        # Create log directory if it doesn't exist
        os.makedirs(self.log_directory, exist_ok=True)
        
        # Generate filename if not provided
        if not filename:
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"drone_sim_{timestamp}.log"
        
        # Create file handler
        log_path = os.path.join(self.log_directory, filename)
        self.file_handler = logging.FileHandler(log_path, mode='a')
        self.file_handler.setFormatter(self.formatter)  # Always use non-colored formatter for files
        self.file_handler.setLevel(level)
        self.logger.addHandler(self.file_handler)
        
        self.info("Logger", f"File logging enabled: {log_path}")
    
    def set_level(self, level: int):
        """
        Change the logging level at runtime.
        
        Args:
            level: New minimum log level (e.g., logging.DEBUG, logging.INFO)
        """
        # Update logger's level
        self.logger.setLevel(level)
        
        # Update console handler's level - always use exactly the level that was specified
        self.console_handler.setLevel(level)
        
        # If file handler exists, keep it at DEBUG level to ensure all logs are captured to file
        if self.file_handler:
            # File handler should always log at DEBUG level or the specified level, whichever is lower
            min_file_level = min(logging.DEBUG, level) if self.verbose else level
            self.file_handler.setLevel(min_file_level)
        
        self.info("Logger", f"Log level changed to: {self._level_to_name(level)}")
    
    def set_debug_level(self, level: int):
        """
        Change the debug verbosity level at runtime.
        
        Args:
            level: New debug level (1-3)
        """
        if level not in [DEBUG_L1, DEBUG_L2, DEBUG_L3]:
            self.warning("Logger", f"Invalid debug level: {level}. Using default level 1.")
            level = DEBUG_L1
            
        self.current_debug_level = level
        self.info("Logger", f"Debug level set to: {level}")
    
    def set_colored_output(self, enabled: bool):
        """
        Enable or disable colored console output.
        
        Args:
            enabled: Whether colored output should be enabled
        """
        self.colored_output = enabled
        
        if enabled:
            self.console_handler.setFormatter(self.colored_formatter)
        else:
            self.console_handler.setFormatter(self.formatter)
            
        self.info("Logger", f"Colored output {'enabled' if enabled else 'disabled'}")
    
    def _level_to_name(self, level: int) -> str:
        """Convert a logging level to its name."""
        level_names = {
            logging.DEBUG: "DEBUG",
            logging.INFO: "INFO", 
            logging.WARNING: "WARNING",
            logging.ERROR: "ERROR",
            logging.CRITICAL: "CRITICAL"
        }
        
        # Try direct lookup first
        if level in level_names:
            return level_names[level]
        
        # If not found, handle common level values that might be used
        if level == 10:      # Common value for DEBUG
            return "DEBUG"
        elif level == 20:    # Common value for INFO 
            return "INFO"
        elif level == 30:    # Common value for WARNING
            return "WARNING"
        elif level == 40:    # Common value for ERROR
            return "ERROR"  
        elif level == 50:    # Common value for CRITICAL
            return "CRITICAL"
        else:
            return f"UNKNOWN ({level})"
    
    def debug(self, module: str, message: str):
        """Log a debug message from a specific module."""
        self.logger.debug(f"[{module}] {message}")
    
    def debug_at_level(self, level: int, module: str, message: str):
        """
        Log a debug message with a specific debug level.
        Message will only be logged if the configured debug_level is >= the specified level.
        
        Args:
            level: Debug level required for this message (1-3)
            module: The name of the module generating the log
            message: The message to log
        """
        if not self.verbose:
            return
            
        if level <= self.current_debug_level:
            self.logger.debug(f"[{module}][L{level}] {message}")
    
    def info(self, module: str, message: str):
        """Log an info message from a specific module."""
        self.logger.info(f"[{module}] {message}")
    
    def warning(self, module: str, message: str):
        """Log a warning message from a specific module."""
        self.logger.warning(f"[{module}] {message}")
    
    def error(self, module: str, message: str):
        """Log an error message from a specific module."""
        # Ensure the message actually gets to the logger regardless of level settings
        self.logger.error(f"[{module}] {message}")
    
    def critical(self, module: str, message: str):
        """Log a critical message from a specific module."""
        # Ensure the message actually gets to the logger regardless of level settings
        self.logger.critical(f"[{module}] {message}")
    
    def verbose_log(self, module: str, message: str, level: Union[Literal["debug"], Literal["info"]] = "debug"):
        """
        Log a message only if verbose mode is enabled.
        
        Args:
            module: The name of the module generating the log
            message: The message to log
            level: The level to log at when verbose is enabled (debug or info)
        """
        if not self.verbose:
            return
            
        if level == "info":
            self.info(module, message)
        else:
            self.debug(module, message)
    
    def shutdown(self):
        """Properly close all handlers."""
        if self.file_handler:
            self.file_handler.close()
            self.logger.removeHandler(self.file_handler)
        
        self.console_handler.close()
        self.logger.removeHandler(self.console_handler)


# Convenience function to get logger instance
def get_logger():
    """Get the singleton Logger instance."""
    return Logger.get_instance() 
