"""
Configuration options for the MeesmanScraper python package. MeesmanScraper can only be configured using a configuration
file.
"""

import configparser
import os
import os.path

CONFIG_PATHS = ['meesman.conf', '~/.meesman.conf', '/etc/meesman.conf']


def get_configuration(path: str = None) -> configparser.ConfigParser:
    """ Parse the configuration from one or more file(s) and the environment variables """
    file_config = _read_config(path)
    return file_config


def _read_config(path: str = None) -> configparser.ConfigParser:
    """ Read the configuration file.

    If path is given, then the function will try to load the configuration file from this path.
    If not, the function will look for local configuration files first and then for global
    configuration files.
    """
    config = configparser.ConfigParser()
    if path:
        if not os.path.exists(path):
            print('Configuration file {} does not exist'.format(path))
        config.read(path)
    else:
        config.read(CONFIG_PATHS)

    return config
