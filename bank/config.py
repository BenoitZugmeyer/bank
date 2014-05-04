import yaml
import os
from .util import YamlLoader, YamlDumper


class Config(object):

    root_path = None

    def __init__(self, config, root_path=None):
        self._config = config or {}
        self.root_path = os.getcwd() if root_path is None else root_path

    def _cast(self, value):
        if isinstance(value, dict) or value is None:
            return Config(value, self.root_path)
        elif isinstance(value, list):
            return tuple(self._cast(v) for v in value)
        else:
            return value

    def __getattr__(self, attr):
        return self.get(attr)

    def __repr__(self):
        return 'Config({!r}, root_path={!r})'\
            .format(self._config, self.root_path)

    def __iter__(self):
        return (
            (key, self._cast(value))
            for key, value in self._config.items()
        )

    def __bool__(self):
        return bool(self._config)

    def __json__(self):
        return self._config

    def get(self, attr, default=None):
        return self._cast(self._config.get(attr, default))

    def getpath(self, attr, default=None):
        value = self.get(attr, default)
        if value is None:
            raise Exception('Can\'t find path for {}'.format(attr))
        return os.path.abspath(os.path.join(
            self.root_path,
            os.path.expanduser(value)))


YamlDumper.add_representer(
    Config,
    lambda r, c: YamlDumper.represent_dict(r, c._config))


def from_yaml(path, default=None):
    if default is not None:
        if not path or not os.path.isfile(path):
            return Config(default)

    with open(path, 'rb') as config_fp:
        raw = yaml.load(config_fp, YamlLoader)

    return Config(raw, os.path.dirname(path))


if __name__ == '__main__':
    import sys

    config = from_yaml(sys.argv[1])

    for g in config.graphs:
        print(g)

    print(config.getpath('blih', 'bank.db'))
