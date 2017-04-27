# Copyright 2017 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0+

import logging
import subprocess
import uuid
import os.path
import shutil
import yaml
from uuid import uuid4
from xivo.rest_api_helpers import APIException

logger = logging.getLogger(__name__)


class UnsupportedDownloadMethod(APIException):

    def __init__(self):
        super().__init__(status_code=501,
                         message='Unsupported download method',
                         error_id='unsupported_download_method',
                         details={})


class DownloadError(APIException):

    def __init__(self, **details):
        super().__init__(status_code=400,
                         message='Download failed',
                         error_id='download_failed',
                         details=details)


class GitDownloader(object):

    def __init__(self, download_dir):
        self._download_dir = download_dir

    def download(self, url):
        filename = os.path.join(self._download_dir, str(uuid.uuid4()))
        logger.debug('git cloning %s into %s', url, filename)
        cmd = ['git', 'clone', '--depth', '1', url, filename]

        with subprocess.Popen(cmd, stderr=subprocess.PIPE) as proc:
            error_msg = proc.stderr.read().decode('utf-8')

        if proc.returncode:
            logger.error('failed to clone: %s', error_msg)
            logger.debug('failed git command: %s', ' '.join(cmd))
            raise DownloadError(message=error_msg, url=url)

        return filename


class UndefinedDownloader(object):

    def __init__(self, base_dir):
        pass

    def download(self, url):
        raise UnsupportedDownloadMethod()


class InstallContext(object):

    def __init__(self, config, url, method):
        self.uuid = str(uuid4())
        self.url = url
        self.method = method
        self.download_path = None
        self.extract_path = None
        self.metadata_filename = None
        self.metadata_base_filename = config['default_metadata_filename']
        self.plugin_dir = config['plugin_dir']
        self.extract_dir = config['extract_dir']
        self.installer_base_filename = config['default_install_filename']

    def with_download_path(self, download_path):
        self.download_path = download_path
        self.extract_path = os.path.join(self.extract_dir, self.uuid)
        return self

    def with_extract_path(self, extract_path):
        self.extract_path = extract_path
        self.metadata_filename = os.path.join(self.extract_path, self.metadata_base_filename)
        return self

    def with_metadata(self, metadata):
        self.metadata = metadata
        self.namespace = metadata['namespace']
        self.name = metadata['name']
        self.plugin_path = os.path.join(self.plugin_dir, self.namespace, self.name)
        self.installer_path = os.path.join(self.plugin_path, self.installer_base_filename)
        return self


class PluginService(object):

    def __init__(self, config, worker):
        download_dir = config['download_dir']
        self._config = config
        self._worker = worker

        self._downloaders = {
            'git': GitDownloader(download_dir),
        }
        self._downloaders.setdefault(UndefinedDownloader(download_dir))

    def build(self, ctx):
        logger.debug('building %s/%s using %s as %s',
                     ctx.namespace, ctx.name, ctx.installer_path, os.getuid())
        cmd = [ctx.installer_path, 'build']
        subprocess.Popen(cmd, cwd=ctx.plugin_path).wait()
        return ctx

    def create(self, url, method):
        ctx = InstallContext(self._config, url, method)
        logger.debug('create [%s] %s', method, url)
        ctx = self.download(ctx)
        ctx = self.extract(ctx)
        ctx = self.move(ctx)
        ctx = self.build(ctx)
        ctx = self.install(ctx)

        return ctx.uuid

    def download(self, ctx):
        download_path = self._downloaders[ctx.method].download(ctx.url)
        return ctx.with_download_path(download_path)

    def extract(self, ctx):
        shutil.rmtree(ctx.extract_path, ignore_errors=True)
        shutil.move(ctx.download_path, ctx.extract_path)
        metadata_filename = os.path.join(ctx.extract_path, ctx.metadata_base_filename)
        with open(metadata_filename, 'r') as f:
            metadata = yaml.safe_load(f)
        return ctx.with_metadata(metadata)

    def install(self, ctx):
        self._worker.install(ctx)
        return ctx

    def move(self, ctx):
        shutil.rmtree(ctx.plugin_path, ignore_errors=True)
        shutil.move(ctx.extract_path, ctx.plugin_path)
        return ctx
