# Copyright 2017 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0+

import logging
import os
import re
import yaml
from .exceptions import InvalidPackageNameException
from . import debian

logger = logging.getLogger(__name__)


class PluginDB(object):

    def __init__(self, config):
        self._config = config
        self._debian_package_section = config['debian_package_section']
        self._debian_package_db = debian.PackageDB()

    def count(self):
        return len(self.list_())

    def is_installed(self, namespace, name):
        return Plugin(self._config, namespace, name).is_installed()

    def list_(self):
        result = []
        debian_packages = self._debian_package_db.list_installed_packages(self._debian_package_section)
        for debian_package in debian_packages:
            try:
                plugin = Plugin.from_debian_package(self._config, debian_package)
                result.append(plugin.metadata())
            except (IOError, InvalidPackageNameException):
                logger.info('no metadata file found for %s/%s', plugin.namespace, plugin.name)
        return result


class Plugin(object):

    def __init__(self, config, namespace, name):
        self.namespace = namespace
        self.name = name
        self.metadata_filename = os.path.join(
            config['metadata_dir'],
            self.namespace,
            self.name,
            config['default_metadata_filename'],
        )
        self._metadata = None

    def is_installed(self):
        try:
            return self.metadata() is not None
        except IOError:
            return False

    def metadata(self):
        if not self._metadata:
            with open(self.metadata_filename, 'r') as f:
                self._metadata = yaml.load(f)

        return self._metadata

    @staticmethod
    def _extract_namespace_and_name(package_name_prefix, package_name):
        package_name_pattern = re.compile(r'^{}-([a-z0-9-]+)-([a-z0-9]+)$'.format(package_name_prefix))
        matches = package_name_pattern.match(package_name)
        if not matches:
            raise InvalidPackageNameException(package_name)
        return matches.group(2), matches.group(1)

    @classmethod
    def from_debian_package(cls, config, debian_package_name):
        package_name_prefix = config['default_debian_package_prefix']
        namespace, name = cls._extract_namespace_and_name(package_name_prefix, debian_package_name)
        return cls(config, namespace, name)
