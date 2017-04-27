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


class PluginService(object):

    def __init__(self, worker):
        self._plugin_dir = '/var/lib/wazo-plugind/plugins'
        self._download_dir = '/var/lib/wazo-plugind/downloads'
        self._tmp_dir = '/var/lib/wazo-plugind/tmp'
        self._metadata_filename = 'package.yml'
        self._downloaders = {
            'git': GitDownloader(self._download_dir),
        }
        self._downloaders.setdefault(UndefinedDownloader(self._download_dir))
        self._worker = worker

    def build(self, namespace, name):
        installer = self._get_installer_path(namespace, name)
        dir = os.path.dirname(installer)
        logger.debug('building %s/%s using %s as %s', namespace, name, installer, os.getuid())
        cmd = [installer, 'build']
        subprocess.Popen(cmd, cwd=dir).wait()

    def create(self, url, method):
        uuid = str(uuid4())
        logger.debug('create [%s] %s', method, url)
        downloaded_path = self.download(method, url)
        extracted_path = self.extract(downloaded_path)
        namespace, name = self._get_plugin_namespace_and_name(extracted_path)
        self.move(extracted_path, namespace, name)

        self.build(namespace, name)
        self.install(namespace, name)

        return uuid

    def download(self, method, url):
        return self._downloaders[method].download(url)

    def extract(self, download_path):
        # TODO: extract is not really extract since git sources are already extracted
        extract_path = os.path.join(self._tmp_dir, str(uuid.uuid4()))
        shutil.rmtree(extract_path, ignore_errors=True)
        shutil.move(download_path, extract_path)
        return extract_path

    def install(self, namespace, name):
        installer = self._get_installer_path(namespace, name)
        dir = os.path.dirname(installer)
        logger.debug('installing %s/%s using %s', namespace, name, installer)
        self._worker.execute([installer, 'install'], cwd=dir)

    def move(self, extracted_path, namespace, name):
        plugin_path = os.path.join(self._plugin_dir, namespace, name)
        shutil.rmtree(plugin_path, ignore_errors=True)
        shutil.move(extracted_path, plugin_path)

    def _delete(self, path):
        logger.debug('deleting %s', path)
        shutil.rmtree(path, ignore_errors=True)

    def _get_installer_path(self, namespace, name):
        installer = os.path.join(self._plugin_dir, namespace, name, 'package.sh')
        if not os.path.exists(installer):
            # make this an API error
            raise Exception('No installer for plugin %s/%s', namespace, name)

        return installer

    def _get_plugin_namespace_and_name(self, path):
        metadata_file = os.path.join(path, self._metadata_filename)
        if not os.path.exists(metadata_file):
            # TODO make this an API error
            raise Exception('No package.yml')

        with open(metadata_file, 'r') as f:
            metadata = yaml.safe_load(f)

        namespace, name = metadata.get('namespace'), metadata.get('name')
        if not namespace or not name:
            # TODO: API error
            raise Exception('Missing metadata fields: %s', [f for f in (namespace, name) if not f])

        return namespace, name
