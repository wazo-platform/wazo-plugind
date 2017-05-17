# Copyright 2017 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0+

import logging
import uuid
import os
import os.path
import re
import shutil
import yaml
from . import db, debian
from .exceptions import (
    InvalidNamespaceException,
    InvalidNameException,
    PluginNotFoundException,
    UnsupportedDownloadMethod,
)
from .helpers import exec_and_log
from .context import Context

logger = logging.getLogger(__name__)


class GitDownloader(object):

    def __init__(self, download_dir):
        self._download_dir = download_dir

    def download(self, url):
        filename = os.path.join(self._download_dir, str(uuid.uuid4()))
        cmd = ['git', 'clone', '--depth', '1', url, filename]

        proc = exec_and_log(logger.debug, logger.error, cmd)
        if proc.returncode:
            raise Exception('Download failed {}'.format(url))

        return filename


class UndefinedDownloader(object):

    def __init__(self, base_dir):
        pass

    def download(self, url):
        raise UnsupportedDownloadMethod()


class PluginService(object):

    valid_namespace = re.compile(r'^[a-z0-9]+$')
    valid_name = re.compile(r'^[a-z0-9-]+$')

    def __init__(self, config, worker, status_publisher):
        download_dir = config['download_dir']
        self._build_dir = config['build_dir']
        self._deb_file = '{}.deb'.format(self._build_dir)
        self._config = config
        self._worker = worker
        self._debian_file_generator = debian.Generator.from_config(config)
        self._status_publisher = status_publisher

        self._downloaders = {
            'git': GitDownloader(download_dir),
        }
        self._undefined_downloader = UndefinedDownloader(download_dir)
        self._plugin_db = db.PluginDB(config)

    def _exec(self, ctx, *args, **kwargs):
        log_debug = ctx.get_logger(logger.debug)
        log_error = ctx.get_logger(logger.error)
        exec_and_log(log_debug, log_error, *args, **kwargs)

    def build(self, ctx):
        namespace, name = ctx.metadata['namespace'], ctx.metadata['name']
        if self.valid_namespace.match(namespace) is None:
            raise InvalidNamespaceException()
        if self.valid_name.match(name) is None:
            raise InvalidNameException()
        installer_path = os.path.join(ctx.extract_path, self._config['default_install_filename'])
        ctx.log(logger.debug, 'building %s/%s', namespace, name)
        cmd = [installer_path, 'build']
        self._exec(ctx, cmd, cwd=ctx.extract_path)
        return ctx.with_fields(installer_path=installer_path, namespace=namespace, name=name)

    def count(self):
        return self._plugin_db.count()

    def debianize(self, ctx):
        ctx.log(logger.debug, 'debianizing %s/%s', ctx.namespace, ctx.name)
        ctx = self._debian_file_generator.generate(ctx)
        cmd = ['dpkg-deb', '--build', ctx.pkgdir]
        self._exec(ctx, cmd, cwd=ctx.extract_path)
        deb_path = os.path.join(ctx.extract_path, self._deb_file)
        return ctx.with_fields(package_deb_file=deb_path)

    def package(self, ctx):
        ctx.log(logger.debug, 'packaging %s/%s', ctx.namespace, ctx.name)
        pkgdir = os.path.join(ctx.extract_path, self._build_dir)
        os.makedirs(pkgdir)
        cmd = ['fakeroot', ctx.installer_path, 'package']
        self._exec(ctx, cmd, cwd=ctx.extract_path, env=dict(os.environ, pkgdir=pkgdir))
        installed_plugin_data_path = os.path.join(pkgdir, 'usr/lib/wazo-plugind/plugins', ctx.namespace, ctx.name)
        os.makedirs(installed_plugin_data_path)
        plugin_data_path = os.path.join(ctx.extract_path, self._config['plugin_data_dir'])
        cmd = ['fakeroot', 'cp', '-R', plugin_data_path, installed_plugin_data_path]
        self._exec(ctx, cmd, cwd=ctx.extract_path)
        return ctx.with_fields(pkgdir=pkgdir)

    def create(self, url, method):
        ctx = Context(self._config, url=url, method=method)
        ctx.log(logger.info, 'installing %s...', url)
        self._status_publisher.install(ctx, 'starting')
        self._status_publisher.install(ctx, 'downloading')
        ctx = self.download(ctx)
        self._status_publisher.install(ctx, 'extracting')
        ctx = self.extract(ctx)
        self._status_publisher.install(ctx, 'building')
        ctx = self.build(ctx)
        self._status_publisher.install(ctx, 'packaging')
        ctx = self.package(ctx)
        ctx = self.debianize(ctx)
        self._status_publisher.install(ctx, 'installing')
        ctx = self.install(ctx)
        self._status_publisher.install(ctx, 'completed')
        ctx.log(logger.info, 'install completed')

        return ctx.uuid

    def download(self, ctx):
        ctx.log(logger.debug, 'downloading %s', ctx.url)
        downloader = self._downloaders.get(ctx.method, self._undefined_downloader)
        download_path = downloader.download(ctx.url)
        return ctx.with_fields(download_path=download_path)

    def extract(self, ctx):
        extract_path = os.path.join(self._config['extract_dir'], ctx.uuid)
        ctx.log(logger.debug, 'extracting %s to %s', ctx.url, extract_path)
        shutil.rmtree(extract_path, ignore_errors=True)
        shutil.move(ctx.download_path, extract_path)
        metadata_filename = os.path.join(extract_path, self._config['default_metadata_filename'])
        with open(metadata_filename, 'r') as f:
            metadata = yaml.safe_load(f)
        return ctx.with_fields(
            metadata=metadata,
            extract_path=extract_path,
        )

    def install(self, ctx):
        ctx = self._worker.install(ctx)
        return ctx

    def list_(self):
        return self._plugin_db.list_()

    def delete(self, namespace, name):
        ctx = Context(self._config, namespace=namespace, name=name)
        ctx.log(logger.info, 'uninstalling %s/%s...', namespace, name)
        self._status_publisher.uninstall(ctx, 'starting')
        plugin = self._plugin_db.get_plugin(namespace, name)
        if not plugin.is_installed():
            raise PluginNotFoundException(namespace, name)
        ctx.with_fields(package_name=plugin.debian_package_name)
        self._status_publisher.uninstall(ctx, 'removing')
        ctx = self.uninstall(ctx)
        ctx.log(logger.info, 'uninstall completed')
        self._status_publisher.uninstall(ctx, 'completed')

        return ctx.uuid

    def uninstall(self, ctx):
        self._worker.uninstall(ctx)
        return ctx
