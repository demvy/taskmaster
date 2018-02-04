
import yaml


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


if __name__ == "__main__":
    try:
        cfg = parse_config()
        for section in cfg:
            print section
        print cfg
    except Exception as e:
        print e
