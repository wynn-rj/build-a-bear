import argparse
import os
import re
import shlex
import subprocess
import sys
import yaml

# Taken from https://github.com/JonathonReinhart/scuba/blob/master/scuba/config.py
class Loader(yaml.SafeLoader):
    def __init__(self, stream):
        self._root = os.path.split(stream.name)[0]
        self._cache = dict()
        super(Loader, self).__init__(stream)

    def from_yaml(self, node):
        '''
        Implementes a !from_yaml constructor with the following syntax:
            !from_yaml filename key
        Arguments:
            filename:   Filename of external YAML document from which to load,
                        relative to the current YAML file.
            key:        Key from external YAML document to return,
                        using a dot-separated syntax for nested keys.
        Examples:
            !from_yaml external.yml pop
            !from_yaml external.yml foo.bar.pop
            !from_yaml "another file.yml" "foo bar.snap crackle.pop"
        '''

        # Load the content from the node, as a scalar
        content = self.construct_scalar(node)

        # Split on unquoted spaces
        try:
            parts = shlex.split(content)
        except UnicodeEncodeError:
            raise yaml.YAMLError('Non-ASCII arguments to !from_yaml are unsupported')

        if len(parts) != 2:
            raise yaml.YAMLError('Two arguments expected to !from_yaml')
        filename, key = parts

        # path is relative to the current YAML document
        path = os.path.join(self._root, filename)

        # Load the other YAML document
        doc = self._cache.get(path)
        if not doc:
            with open(path, 'r') as other_file:
                doc = yaml.load(other_file, self.__class__)
                self._cache[path] = doc

        # Retrieve the key
        try:
            cur = doc
            # Use a negative look-behind to split the key on non-escaped '.' characters
            for k in re.split(r'(?<!\\)\.', key):
		# Be sure to replace any escaped '.' characters with *just* the '.'
                cur = cur[k.replace('\\.', '.')]
        except KeyError:
            raise yaml.YAMLError('Key "{}" not found in {}'.format(key, filename))
        return cur

Loader.add_constructor('!from_yaml', Loader.from_yaml)

def read_yaml(file):
    """Read a yaml file with the !from_yaml loader"""
    with open(file, 'r') as yfile:
        return yaml.load(yfile, Loader)

def get_docker_image():
    if not os.path.isfile('.scuba.yml'):
        print('Could not find scuba config file. Aborting..')
        sys.exit(1)
    scuba_yml = read_yaml('.scuba.yml')
    try:
        image = scuba_yml['image']

    except (yaml.YAMLError, KeyError) as err:
        print('An error occured reading .scuba.yml')
        print(err)
        sys.exit(1)

def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument('dir', help='The project directory to run bear on')
    parser.add_argument('--build-cmd', default='scons', help='The system being'
                        'used to build the project')
    parser.add_argument('-f', '--force', action='store_true', help='Force a '
                        'rebuild of the docker image')
    return parser.parse_args()

def main():
    args = parse_args()
    os.chdir(args.dir)

if __name__ == '__main__':
    main()
