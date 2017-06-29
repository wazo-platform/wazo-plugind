# Copyright 2017 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0+

import re
import subprocess
from . import db
from .exceptions import (
    PluginAlreadyInstalled,
    PluginValidationException,
)
from .schema import new_plugin_metadata_schema

_DEFAULT_PLUGIN_FORMAT_VERSION = 0


def exec_and_log(stdout_logger, stderr_logger, *args, **kwargs):
    p = subprocess.Popen(*args, stdout=subprocess.PIPE, stderr=subprocess.PIPE, **kwargs)
    out, err = p.communicate()
    cmd = ' '.join(args[0])
    if out:
        stdout_logger('%s\n==== STDOUT ====\n%s==== END ====', cmd, out.decode('utf8'))
    if err:
        stdout_logger('%s\n==== STDERR====\n%s==== END ====', cmd, err.decode('utf8'))
    return p


class Validator(object):

    valid_namespace = re.compile(r'^[a-z0-9]+$')
    valid_name = re.compile(r'^[a-z0-9-]+$')
    required_fields = ['name', 'namespace', 'version']

    def __init__(self, plugin_db, wazo_version_finder):
        self._db = plugin_db
        self._wazo_version_finder = wazo_version_finder

    def validate(self, metadata):
        current_version = self._wazo_version_finder.get_version()

        body, errors = new_plugin_metadata_schema(current_version).load(metadata)
        if errors:
            raise PluginValidationException(errors)

        if self._db.is_installed(metadata['namespace'], metadata['name'], metadata['version']):
            raise PluginAlreadyInstalled(metadata['namespace'], metadata['name'])

    @classmethod
    def new_from_config(cls, config):
        plugin_db = db.PluginDB(config)
        wazo_version_finder = _WazoVersionFinder()
        return cls(plugin_db, wazo_version_finder)


class _WazoVersionFinder(object):

    def get_version(self):
        return '17.10'
