# Copyright 2017 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0+

import logging
import uuid
import os
import os.path
import re
import shutil
import subprocess
import yaml
from uuid import uuid4
from . import debian
from .exceptions import (
    InvalidMetadata,
    InvalidNamespaceException,
    InvalidNameException,
    UnsupportedDownloadMethod,
)
from .helpers import exec_and_log

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


class InstallContext(object):

    valid_namespace = re.compile(r'^[a-z0-9]+$')
    valid_name = re.compile(r'^[a-z0-9-]+$')

    def __init__(self, config, url, method):
        self.uuid = str(uuid4())
        self.url = url
        self.method = method
        self.download_path = None
        self.extract_path = None
        self.metadata_filename = None
        self.debian_package = None
        self.package_deb_file = None
        self.metadata_base_filename = config['default_metadata_filename']
        self.plugin_dir = config['plugin_dir']
        self.plugin_data_dir = config['plugin_data_dir']
        self.extract_dir = config['extract_dir']
        self.installer_base_filename = config['default_install_filename']
        self.debian_package_prefix = config['default_debian_package_prefix']
        self.metadata_dir = config['metadata_dir']

    def log_debug(self, msg, *args):
        self._log(logger.debug, msg, *args)

    def log_error(self, msg, *args):
        self._log(logger.error, msg, *args)

    def log_info(self, msg, *args):
        self._log(logger.info, msg, *args)

    def with_built(self):
        self._built = True

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
        if self.valid_namespace.match(self.namespace) is None:
            raise InvalidNamespaceException()
        self.name = metadata['name']
        if self.valid_name.match(self.name) is None:
            raise InvalidNameException()
        if 'version' not in metadata:
            raise InvalidMetadata('no version')
        self.package_name = '{prefix}-{name}-{namespace}'.format(
            prefix=self.debian_package_prefix,
            name=self.name,
            namespace=self.namespace,
        )
        self.plugin_path = os.path.join(self.plugin_dir, self.namespace, self.name)
        self.installer_path = os.path.join(self.plugin_path, self.installer_base_filename)
        self.plugin_data_path = os.path.join(self.plugin_path, self.plugin_data_dir)
        self.destination_plugin_path = os.path.join(self.metadata_dir, self.namespace, self.name)
        self.destination_plugin_data_path = os.path.join(self.destination_plugin_path, self.plugin_data_dir)
        return self

    def with_template_context(self, template_context):
        self.template_context = template_context
        return self

    def with_debian_dir(self, debian_dir):
        self.debian_dir = debian_dir
        return self

    def with_deb_file(self, deb_file):
        self.package_deb_file = deb_file
        return self

    def with_pkgdir(self, pkgdir):
        self.pkgdir = pkgdir
        self.plugin_data_dst = os.path.join(pkgdir, self.destination_plugin_data_path)
        return self

    def with_deb_package(self):
        filename = '{package_name}.deb'.format(package_name=self.package_name)
        self.package_deb_file = os.path.join(self.plugin_path, filename)
        return self

    def _log(self, log_fn, msg, *args):
        log_fn('[%s] '+msg, self.uuid, *args)


class PluginService(object):

    def __init__(self, config, worker):
        download_dir = config['download_dir']
        self._build_dir = config['build_dir']
        self._deb_file = '{}.deb'.format(self._build_dir)
        self._config = config
        self._worker = worker
        self._debian_file_generator = debian.Generator.from_config(config)

        self._downloaders = {
            'git': GitDownloader(download_dir),
        }
        self._undefined_downloader = UndefinedDownloader(download_dir)

    def _exec(self, ctx, *args, **kwargs):
        exec_and_log(ctx.log_debug, ctx.log_error, *args, **kwargs)

    def build(self, ctx):
        ctx.log_debug('building %s/%s', ctx.namespace, ctx.name)
        cmd = [ctx.installer_path, 'build']
        self._exec(ctx, cmd, cwd=ctx.plugin_path)
        return ctx

    def debianize(self, ctx):
        ctx.log_debug('debianizing %s/%s', ctx.namespace, ctx.name)
        ctx = self._debian_file_generator.generate(ctx)
        cmd = ['dpkg-deb', '--build', ctx.pkgdir]
        self._exec(ctx, cmd, cwd=ctx.plugin_path)
        deb_path = os.path.join(ctx.plugin_path, self._deb_file)
        return ctx.with_deb_file(deb_path)

    def package(self, ctx):
        ctx.log_debug('packaging %s/%s', ctx.namespace, ctx.name)
        pkgdir = os.path.join(ctx.plugin_path, self._build_dir)
        os.makedirs(pkgdir)
        cmd = ['fakeroot', ctx.installer_path, 'package']
        self._exec(ctx, cmd, cwd=ctx.plugin_path, env=dict(os.environ, pkgdir=pkgdir))
        installed_plugin_data_path = os.path.join(pkgdir, 'usr/lib/wazo-plugind/plugins', ctx.namespace, ctx.name)
        os.makedirs(installed_plugin_data_path)
        cmd = ['fakeroot', 'cp', '-R', ctx.plugin_data_path, installed_plugin_data_path]
        self._exec(ctx, cmd, cwd=ctx.plugin_path)
        return ctx.with_pkgdir(pkgdir)

    def create(self, url, method):
        ctx = InstallContext(self._config, url, method)
        ctx.log_info('installing %s...', url)
        ctx = self.download(ctx)
        ctx = self.extract(ctx)
        ctx = self.move(ctx)
        ctx = self.build(ctx)
        ctx = self.package(ctx)
        ctx = self.debianize(ctx)
        ctx = self.install(ctx)
        ctx.log_info('install completed')

        return ctx.uuid

    def download(self, ctx):
        ctx.log_debug('downloading %s', ctx.url)
        downloader = self._downloaders.get(ctx.method, self._undefined_downloader)
        download_path = downloader.download(ctx.url)
        return ctx.with_download_path(download_path)

    def extract(self, ctx):
        ctx.log_debug('extracting %s to %s', ctx.url, ctx.extract_path)
        shutil.rmtree(ctx.extract_path, ignore_errors=True)
        shutil.move(ctx.download_path, ctx.extract_path)
        metadata_filename = os.path.join(ctx.extract_path, ctx.metadata_base_filename)
        with open(metadata_filename, 'r') as f:
            metadata = yaml.safe_load(f)
        return ctx.with_metadata(metadata)

    def install(self, ctx):
        self._worker.install(ctx)
        return ctx

    def list_(self):
        filter_ = "${binary:Package} ${Section}\n"
        cmd = ['dpkg-query', '-W', '-f={}'.format(filter_)]
        p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        out, err = p.communicate()
        debian_packages = []
        for line in out.decode('utf-8').split('\n'):
            debian_package_name, _, section = line.partition(' ')
            if section != 'wazo-plugind-plugin':
                continue
            logger.debug('[%s] [%s]', debian_package_name, section)
            debian_packages.append(debian_package_name)
        result = []
        package_name_pattern = re.compile(r'^wazo-plugind-([a-z0-9-]+)-([a-z0-9]+)$')
        for debian_package in debian_packages:
            logger.debug('*** %s ***', debian_package)
            matches = package_name_pattern.match(debian_package)
            if not matches:
                logger.debug('package %s does not have a name matching the expected pattern', debian_package)
                continue
            name, namespace = matches.group(1), matches.group(2)
            metadata = self._get_metadata(namespace, name)
            result.append(metadata)
        return result

    def _get_metadata(self, namespace, name):
        metadata_file = os.path.join('/usr/lib/wazo-plugind/plugins', namespace, name, 'wazo', 'plugin.yml')
        with open(metadata_file, 'r') as f:
            return yaml.load(f)

    def move(self, ctx):
        ctx.log_debug('moving %s to %s', ctx.extract_path, ctx.plugin_path)
        shutil.rmtree(ctx.plugin_path, ignore_errors=True)
        shutil.move(ctx.extract_path, ctx.plugin_path)
        return ctx
