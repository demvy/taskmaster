
import yaml
import logging
import signal
import time
from datetime import datetime as dt


def parse_config():
    """
    Parse config for taskmaster daemon

    Returns:
        dict with options of config
    """
    with open("taskmaster.yaml", 'r') as ymlfile:
        try:
            cfg = yaml.load(ymlfile)
            return cfg
        except yaml.YAMLError as exc:
            raise exc

new_cfg = {}

def signal_handler(signum, frame):
    global new_cfg
    new_cfg = parse_config()
    print("new_cfg created")
    # implement
    #  !!!!! reload_config()

try:
    cfg = parse_config()
    if cfg['taskmasterd']['nodaemon']:
        logging.basicConfig(level=logging.DEBUG)
    else:
        try:
            filename = cfg['taskmasterd']['logfile']
            logging.basicConfig(filename=filename, level=logging.DEBUG)
        except KeyError as e:
            logging.basicConfig(filename=dt.strftime(dt.now(), '%Y.%m.%d-%H:%M:%S'), level=logging.DEBUG)
except Exception as e:
    print(e)
    logging.error(e)


if __name__ == "__main__":
    print(cfg)
    signal.signal(signal.SIGHUP, signal_handler)
    while True:
        time.sleep(3)
        print(cfg)
    #logging.debug("In main test logging")