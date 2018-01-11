# Copyright 2018 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0+

import logging
import re

from wazo_plugind.db import PluginDB
from wazo_plugind.schema import new_plugin_metadata_schema
from wazo_plugind.exceptions import (
    PluginAlreadyInstalled,
    PluginValidationException,
)

logger = logging.getLogger(__name__)


class Validator(object):

    valid_namespace = re.compile(r'^[a-z0-9]+$')
    valid_name = re.compile(r'^[a-z0-9-]+$')
    required_fields = ['name', 'namespace', 'version']

    def __init__(self, plugin_db, current_wazo_version, install_params):
        self._db = plugin_db
        self._current_wazo_version = current_wazo_version
        self._install_params = install_params

    def validate(self, metadata):
        logger.debug('Using current version %s', self._current_wazo_version)
        logger.debug('max_wazo_version: %s', metadata.get('max_wazo_version', 'undefined'))

        body, errors = new_plugin_metadata_schema(self._current_wazo_version).load(metadata)
        if errors:
            raise PluginValidationException(errors)
        logger.debug('validated metadata: %s', body)

        if self._install_params['reinstall']:
            return

        if self._db.is_installed(metadata['namespace'], metadata['name'], metadata['version']):
            raise PluginAlreadyInstalled(metadata['namespace'], metadata['name'])

    @classmethod
    def new_from_config(cls, config, current_wazo_version, install_params):
        plugin_db = PluginDB(config)
        return cls(plugin_db, current_wazo_version, install_params)
