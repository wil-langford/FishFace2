import logging
import logging.handlers
import json

import etc.fishface_config as ff_conf

logger = logging.getLogger('fishface')
logger.setLevel(ff_conf.OVERALL_LOG_LEVEL)

formatter = logging.Formatter('%(asctime)s %(name)s %(levelname)s %(message)s')

file_handler = logging.FileHandler(ff_conf.LOG_FILE_PATH)
file_handler.setLevel(ff_conf.FILE_LOG_LEVEL)
file_handler.setFormatter(formatter)
logger.addHandler(file_handler)

if ff_conf.LOG_TO_CONSOLE:
    console_handler = logging.StreamHandler()
    console_handler.setLevel(ff_conf.CONSOLE_LOG_LEVEL)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

if ff_conf.LOG_TO_EMAIL:
    class FishFaceSMTPHandler(logging.handlers.SMTPHandler):
        formatter = logging.Formatter(fmt='[FISHFACE_LOG] %(name)s %(levelname)s')

        def getSubject(self, record):
            return self.formatter.format(record)

    email_handler = FishFaceSMTPHandler(
        mailhost=ff_conf.EMAIL_LOG_SMTP_HOST,
        fromaddr=ff_conf.EMAIL_LOG_FROM_ADDR,
        toaddrs=ff_conf.EMAIL_LOG_TO_ADDRS,
        subject=ff_conf.EMAIL_LOG_SUBJECT,
    )
    email_handler.setLevel(ff_conf.EMAIL_LOG_LEVEL)
    email_handler.setFormatter(formatter)
    logger.addHandler(email_handler)


def dense_log(tag, dict_to_log):
    return 'DENSE_LOG#' + str(tag) + '#' + json.dumps(
        dict_to_log,
        separators=(',', ':'),
    )
