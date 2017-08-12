import logging

def simple_logger():
    logger = logging.getLogger('input_log')
    logger.setLevel(logging.INFO)
    file_handler = logging.FileHandler('transact.log')
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    return logger