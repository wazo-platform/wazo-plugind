# Copyright 2017 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0+

import re
import subprocess
from . import db
from .config import _MAX_PLUGIN_FORMAT_VERSION
from .exceptions import (
    InvalidNamespaceException,
    InvalidNameException,
    InvalidPluginFormatVersion,
    MissingFieldException,
    PluginAlreadyInstalled,
)
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

    def __init__(self, config):
        self._db = db.PluginDB(config)

    def validate(self, metadata):
        for field in self.required_fields:
            if field not in metadata:
                raise MissingFieldException(field)
        namespace, name = metadata['namespace'], metadata['name']
        version = metadata['version']
        if self.valid_namespace.match(namespace) is None:
            raise InvalidNamespaceException()
        if self.valid_name.match(name) is None:
            raise InvalidNameException()
        if int(metadata.get('plugin_format_version', _DEFAULT_PLUGIN_FORMAT_VERSION)) > _MAX_PLUGIN_FORMAT_VERSION:
            raise InvalidPluginFormatVersion(_MAX_PLUGIN_FORMAT_VERSION)
        if self._db.is_installed(namespace, name, version):
            raise PluginAlreadyInstalled(namespace, name)
