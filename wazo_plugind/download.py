# Copyright 2017 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0+

import os
import logging
from . import db
from .exceptions import InvalidInstallParamException, UnsupportedDownloadMethod
from .helpers import exec_and_log
from .schema import PluginInstallSchema

logger = logging.getLogger(__name__)


class _GitDownloader(object):

    def __init__(self, config):
        self._download_dir = config['download_dir']

    def download(self, ctx):
        url, ref = ctx.url, ctx.install_args['ref']
        filename = os.path.join(self._download_dir, ctx.uuid)

        cmd = ['git', 'clone', '--branch', ref, '--depth', '1', url, filename]

        proc = exec_and_log(logger.debug, logger.error, cmd)
        if proc.returncode:
            raise Exception('Download failed {}'.format(url))

        return ctx.with_fields(download_path=filename)


class _MarketDownloader(object):

    _defaults = {'method': 'git'}

    def __init__(self, config, downloader):
        self._market_config = config['market']
        self._downloader = downloader

    def download(self, ctx):
        metadata = self._find_matching_plugin(ctx)
        for key, value in self._defaults.items():
            if key not in metadata:
                metadata[key] = value

        body, errors = PluginInstallSchema().load(metadata)
        if errors:
            raise InvalidInstallParamException(errors)

        ctx = ctx.with_fields(
            url=body['url'],
            method=body.get('method'))

        options = body['options']
        if options:
            ctx = ctx.with_fields(install_args=options)

        return self._downloader.download(ctx)

    def _find_matching_plugin(self, ctx):
        market_config = dict(self._market_config)
        if ctx.url:
            market_config['url'] = ctx.url

        market_proxy = db.MarketProxy(market_config)
        market_db = db.MarketDB(market_proxy)
        return market_db.get(**ctx.install_args)


class _UndefinedDownloader(object):

    def __init__(self, config):
        pass

    def download(self, url):
        raise UnsupportedDownloadMethod()


class Downloader(object):

    def __init__(self, config):
        self._downloaders = {
            'git': _GitDownloader(config),
            'market': _MarketDownloader(config, self),
        }
        self._undefined_downloader = _UndefinedDownloader(config)

    def download(self, ctx):
        impl = self._downloaders.get(ctx.method, self._undefined_downloader)
        return impl.download(ctx)
