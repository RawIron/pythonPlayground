import os
from kazoo.client import KazooClient


# ZOOKEEPER

def read_bytes(zk, key):
    if not zk.exists(key):
        raise ValueError 

    data, stat = zk.get(key)
    if data:
        try:
            print("Version: %s, unicode data: %s" % (stat.version, data.decode("utf-8")))
        except UnicodeDecodeError:
            print("Version: %s, raw data: %s" % (stat.version, data))
    else:
        print("Version: %s, data: None" % (stat.version))

    return data

def write_bytes(zk, key, value):
    if zk.exists(key):
        raise ValueError 

    zk.ensure_path(os.path.dirname(key))
    return zk.create(key, value)


# BACKUP STORAGE

STORAGE_DATA = "/tmp"

def write_to(fname):
    def write(value):
        with open(fname, 'wb') as f:
            f.write(value)
    return write

def read_from(fname):
    def read():
        with open(fname, 'rb') as f:
            value = f.read()
        return value
    return read

def get_backup_for(key):
    return "{path}/{name}.dump".format(path=STORAGE_DATA, name=key.replace("/", "_"))

def create_write(key):
    backup = get_backup_for(key)
    return write_to(backup)

def create_read(key):
    backup = get_backup_for(key)
    return read_from(backup)


# TOOL

def create_backup_operation(zk):
    def backup_value(key):
        write = create_write(key)
        value = read_bytes(zk, key)
        if value:
            write(value)
        return value
    return backup_value

def create_restore_operation(zk):
    def restore_value(key):
        read = create_read(key)
        restored_value = read()
        write_bytes(zk, key, restored_value)
        return restored_value
    return restore_value


def main(options, zk, keys):
    if options['--backup']:
        backup_op = create_backup_operation(zk)
        map(backup_op, keys)

    if options['--restore']:
        restore_op = create_restore_operation(zk)
        map(restore_op, keys)


# TEST

def test_backup(options):
    keys = options['KEYS']
    state = dict()
    for key in keys:
        state[key] = "a_test_value"
    zk = load_scenario_backup_test(state)
    zk.start()
    options['--backup'] = True
    options['--restore'] = False
    main(options, zk, keys)
    zk.stop()

def test_restore(options):
    keys = options['KEYS']
    state = dict()
    zk = load_scenario_restore_test(state)
    zk.start()
    options['--backup'] = False
    options['--restore'] = True
    main(options, zk, keys)
    zk.stop()

def run_tests(options):
    test_backup(options)
    test_restore(options)


# INJECT

def load_scenario_zoo():
    zk = KazooClient(hosts='localhost:2181')
    return zk

class Status(object):
    version = 0.1

class TestClient(object):
    def __init__(self, state):
        self.store = state
        self.stat = Status()
    def start(self):
        pass
    def stop(self):
        pass
    def get(self, key):
        return self.store[key], self.stat
    def exists(self, key):
        return (key in self.store)
    def ensure_path(self, path):
        pass
    def create(self, key, value):
        return value

def load_scenario_backup_test(state):
    zk = TestClient(state)
    return zk

def load_scenario_restore_test(state):
    zk = TestClient(state)
    return zk


from docopt import docopt

_usage="""
Backup or Restore Zookeeper keys

Usage:
  zookeeper_repair (--restore | --backup | --test) KEYS ...

Arguments:
  KEYS    list of keys

Options:
  -h --help   show this
  --backup    backup keys
  --restore   restore keys
  --test      run tests
"""

if __name__ == '__main__':
    options = docopt(_usage)

    if options['--test']:
        run_tests(options)
        exit(1)

    keys = options['KEYS']
    zk = load_scenario_zoo()
    zk.start()
    main(options, zk, keys)
    zk.stop()
