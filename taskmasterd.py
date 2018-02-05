
import yaml
import logging
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
    logging.debug("In main test logging")