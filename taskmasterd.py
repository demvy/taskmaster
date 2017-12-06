
def reading_conf_f():
    with open('taskmaster.conf', 'r+') as conf:
        for line in conf:
            if line == 'config:':
                print(line)
    return {}
