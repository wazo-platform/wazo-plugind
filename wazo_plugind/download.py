# Copyright 2017 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0+

import os
import logging
from . import db
from .exceptions import UnsupportedDownloadMethod
from .helpers import exec_and_log

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

    def __init__(self, config, downloader):
        self._market_config = config['market']
        self._downloader = downloader

    def download(self, ctx):
        metadata = self._find_matching_plugin(ctx)

        # TODO: maybe use the install schema to validate here
        ctx = ctx.with_fields(
            url=metadata['url'],
            # Default to git since only git and market are available at this time
            method=metadata.get('method', 'git'))
        options = metadata.get('options')
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
