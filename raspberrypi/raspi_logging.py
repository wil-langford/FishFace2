import logging

logger = logging.getLogger('raspi')
logger.setLevel(logging.DEBUG)

formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')

LOG_TO_CONSOLE = True
CONSOLE_LOG_LEVEL = logging.INFO
FILE_LOG_LEVEL = logging.DEBUG

console_handler = logging.StreamHandler()
console_handler.setLevel(CONSOLE_LOG_LEVEL)
console_handler.setFormatter(formatter)

file_handler = logging.FileHandler('imagery_server.log')
file_handler.setLevel(FILE_LOG_LEVEL)
file_handler.setFormatter(formatter)

logger.addHandler(file_handler)
if LOG_TO_CONSOLE:
    logger.addHandler(console_handler)