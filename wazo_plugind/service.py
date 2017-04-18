# Copyright 2017 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0+

import logging
import subprocess
import uuid
import os.path
import shutil
from contextlib import contextmanager
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


class PluginService(object):

    def __init__(self):
        self._plugin_dir = '/var/lib/wazo-plugind/plugins'
        self._download_dir = '/var/lib/wazo-plugind/downloads'
        self._downloaders = {
            'git': GitDownloader(self._download_dir),
        }
        self._downloaders.setdefault(UndefinedDownloader(self._download_dir))

    def create(self, namespace, name, url, method):
        logger.debug('installing %s/%s from %s [%s]...', namespace, name, url, method)
        download_path = self.download(method, url)
        self.extract_to(namespace, name, download_path)
        self.install(namespace, name)
        self._delete(download_path)

    def download(self, method, url):
        return self._downloaders[method].download(url)

    def extract_to(self, namespace, name, download_path):
        extract_path = os.path.join(self._plugin_dir, namespace, name)
        logger.debug('extracting %s to %s', download_path, extract_path)
        shutil.rmtree(extract_path, ignore_errors=True)
        shutil.copytree(download_path, extract_path)

    def install(self, namespace, name):
        installer = os.path.join(self._plugin_dir, namespace, name, 'package.sh')
        logger.debug('installing %s/%s at %s', namespace, name, installer)
        # sysconfd_client.execute([installer, 'install'])

    def _delete(self, path):
        logger.debug('deleting %s', path)
        shutil.rmtree(path, ignore_errors=True)
