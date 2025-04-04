import logging
import os


class Config:
    APP_DIR = os.path.abspath(os.path.dirname(__file__))
    PROJECT_ROOT = os.path.abspath(os.path.join(APP_DIR, os.pardir))
    SOCKET_ROOT = "."
    LOG_ROOT = "./"
    LOG_FILE = "acl.log"
    LOG_FORMAT = "%(asctime)s | %(pathname)s:%(lineno)d | %(funcName)s | %(levelname)s | %(message)s "
    LOG_LEVEL = logging.INFO


class ProdConfig(Config):
    LOG_FILE = "acl.log"
    LOG_ROOT = "/var/log/queeriouslabs/"
    LOG_LEVEL = logging.INFO
    SOCKET_ROOT = "/run/queeriouslabs"
