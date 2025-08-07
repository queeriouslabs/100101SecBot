import logging
import os


class ExampleConfig:
    APP_DIR = os.path.abspath(os.path.dirname(__file__))
    PROJECT_ROOT = os.path.abspath(os.path.join(APP_DIR, os.pardir))
    SOCKET_ROOT = os.path.join(APP_DIR, "sockets")
    LOG_ROOT = os.path.join(APP_DIR, "logs")
    LOG_FILE = "acl.log"
    LOG_FORMAT = "%(asctime)s | %(pathname)s:%(lineno)d | %(funcName)s | %(levelname)s | %(message)s "
    LOG_LEVEL = logging.INFO
