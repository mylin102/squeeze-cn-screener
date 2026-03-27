import logging
import sys
import os
from datetime import datetime

def setup_logging(log_level: int = logging.INFO, log_to_file: bool = True):
    """
    Configures logging for the squeeze package.
    """
    logger = logging.getLogger("squeeze")
    logger.setLevel(log_level)
    
    # Avoid duplicate handlers
    if logger.handlers:
        return logger
        
    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    
    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    # File handler
    if log_to_file:
        log_dir = os.path.join(os.getcwd(), "logs")
        if not os.path.exists(log_dir):
            os.makedirs(log_dir)
            
        today = datetime.now().strftime("%Y-%m-%d")
        log_file = os.path.join(log_dir, f"squeeze_{today}.log")
        file_handler = logging.FileHandler(log_file)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
        
    return logger

# Create a default logger instance
logger = setup_logging()
