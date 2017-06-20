# Copyright 2017 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0+

import os
import logging
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


class _UndefinedDownloader(object):

    def __init__(self, config):
        pass

    def download(self, url):
        raise UnsupportedDownloadMethod()


class Downloader(object):

    def __init__(self, config):
        self._downloaders = {
            'git': _GitDownloader(config),
        }
        self._undefined_downloader = _UndefinedDownloader(config)

    def download(self, ctx):
        impl = self._downloaders.get(ctx.method, self._undefined_downloader)
        return impl.download(ctx)
