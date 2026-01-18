import logging
import sys

def setup_logger(name):
    logger = logging.getLogger(name)
    
    # Only configure if the logger doesn't have handlers already
    if not logger.handlers:
        logger.setLevel(logging.INFO)
        
        # Format: Time - Service Name - Level - Message
        formatter = logging.Formatter('%(asctime)s | %(name)-20s | %(levelname)-8s | %(message)s')

        # 1. File Handler (The Audit Trail)
        file_handler = logging.FileHandler("dq_rule_onboarding_audit.log", mode='a')
        file_handler.setFormatter(formatter)
        
        # 2. Console Handler (For terminal)
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(formatter)

        logger.addHandler(file_handler)
        logger.addHandler(console_handler)
        
    return logger