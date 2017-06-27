# Copyright 2017 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0+

import logging
import os
import re
import yaml
import requests
from .exceptions import InvalidPackageNameException
from . import debian

logger = logging.getLogger(__name__)


class AlwaysLast(object):

    def __lt__(self, other):
        return False

    def __gt__(self, other):
        return True


LAST_ITEM = AlwaysLast()


class MarketProxy(object):
    """The MarketProxy is an interface to the plugin market

    The proxy should be used during the execution of an HTTP request. It will fetch the content
    of the market and store it to allow multiple "queries" without having to do multiple HTTP
    requests on the "real" market.

    The proxy will only fetch the content of the market once, it is meant to be instanciated at
    each received HTTP request.
    """

    def __init__(self, market_config):
        self._market_url = market_config['url']
        self._verify = market_config['verify_certificate']
        self._content = {}

    def get_content(self):
        if not self._content:
            self._fetch_plugin_list()
        return self._content

    def _fetch_plugin_list(self):
        response = requests.get(self._market_url, verify=self._verify)
        if response.status_code != 200:
            logger.info('Failed to fetch plugins from the market %s', response.status_code)
            return
        self._content = response.json()['items']


class MarketDB(object):

    def __init__(self, market_proxy):
        self._market_proxy = market_proxy

    def count(self, *args, **kwargs):
        return len(self._market_proxy.get_content())

    def list_(self, *args, **kwargs):
        raw_content = self._market_proxy.get_content()
        sorted_content = self._sort(raw_content, **kwargs)
        return sorted_content

    @staticmethod
    def _sort(content, order=None, direction=None):
        reverse = direction == 'desc'

        def key(element):
            return element.get(order, LAST_ITEM)

        return sorted(content, key=key, reverse=reverse)


class PluginDB(object):

    def __init__(self, config):
        self._config = config
        self._debian_package_section = config['debian_package_section']
        self._debian_package_db = debian.PackageDB()

    def count(self):
        return len(self.list_())

    def get_plugin(self, namespace, name):
        return Plugin(self._config, namespace, name)

    def is_installed(self, namespace, name, version=None):
        return Plugin(self._config, namespace, name).is_installed(version)

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
        self.debian_package_name = '{}-{}-{}'.format(config['default_debian_package_prefix'], name, namespace)
        self.metadata_filename = os.path.join(
            config['metadata_dir'],
            self.namespace,
            self.name,
            config['default_metadata_filename'],
        )
        self._metadata = None

    def is_installed(self, version=None):
        try:
            metadata = self.metadata()
        except IOError:
            return False

        if metadata is None:
            return False
        if version is None:
            return True

        return version == metadata['version']

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
