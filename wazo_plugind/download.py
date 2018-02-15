# Copyright 2017-2018 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0+

import os
import logging
from . import db
from .exceptions import (
    InvalidInstallParamException,
    UnsupportedDownloadMethod,
    DependencyAlreadyInstalledException,
)
from .helpers import exec_and_log
from .schema import PluginInstallSchema
from .db import PluginDB

logger = logging.getLogger(__name__)


class _GitDownloader:

    def __init__(self, config):
        self._download_dir = config['download_dir']

    def download(self, ctx):
        url, ref = ctx.install_options['url'], ctx.install_options['ref']
        filename = os.path.join(self._download_dir, ctx.uuid)

        cmd = ['git', 'clone', '--branch', ref, '--depth', '1', url, filename]

        proc = exec_and_log(logger.debug, logger.error, cmd)
        if proc.returncode:
            raise Exception('Download failed {}'.format(url))

        return ctx.with_fields(download_path=filename)


class _MarketDownloader:

    _defaults = {'method': 'git'}

    def __init__(self, config, downloader):
        self._market_config = config['market']
        self._downloader = downloader

    def download(self, ctx):
        version_info = self._find_matching_plugin(ctx)
        if not version_info:
            ctx.log(logger.debug, 'Ignoring dependency not upgradable: %s', ctx.install_options)
            raise DependencyAlreadyInstalledException()

        for key, value in self._defaults.items():
            if key not in version_info:
                version_info[key] = value

        body, errors = PluginInstallSchema().load(version_info)
        if errors:
            raise InvalidInstallParamException(errors)

        ctx = ctx.with_fields(
            method=body.get('method'))

        options = body['options']
        if options:
            ctx = ctx.with_fields(install_options=options)

        return self._downloader.download(ctx)

    def _already_satisfied(self, plugin_info, required_version):
        installed_version = plugin_info.get('installed_version')
        if not installed_version:
            return False

        if not required_version:
            return True

        return installed_version == required_version

    def _find_matching_plugin(self, ctx):
        plugin_db = PluginDB(ctx.config)
        market_proxy = db.MarketProxy(self._market_config)
        market_db = db.MarketDB(market_proxy, ctx.wazo_version, plugin_db)
        required_version = ctx.install_options.get('version')
        search_params = dict(ctx.install_options)
        search_params.pop('version', None)
        plugin_info = market_db.get(**search_params)

        if self._already_satisfied(plugin_info, required_version):
            ctx.log(logger.info, '%s already satisfies %s', plugin_info, required_version)
            raise DependencyAlreadyInstalledException()

        if not required_version:
            return self._find_first_upgradable_version(plugin_info)

        return self._find_matching_version(plugin_info, required_version)

    def _find_matching_version(self, plugin_info, required_version):
        for version_info in plugin_info.get('versions', []):
            if not version_info['upgradable']:
                continue

            if version_info.get('version') == required_version:
                return version_info

    def _find_first_upgradable_version(self, plugin_info):
        for version_info in plugin_info.get('versions', []):
            if version_info['upgradable'] is True:
                return version_info


class _UndefinedDownloader:

    def __init__(self, config):
        pass

    def download(self, ctx):
        raise UnsupportedDownloadMethod()


class Downloader:

    def __init__(self, config):
        self._downloaders = {
            'git': _GitDownloader(config),
            'market': _MarketDownloader(config, self),
        }
        self._undefined_downloader = _UndefinedDownloader(config)

    def download(self, ctx):
        impl = self._downloaders.get(ctx.method, self._undefined_downloader)
        return impl.download(ctx)
