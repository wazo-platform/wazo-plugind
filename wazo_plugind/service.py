# Copyright 2017 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0+

import logging
import subprocess
import uuid
import os
import os.path
import re
import shutil
import yaml
from uuid import uuid4
import jinja2
from xivo.rest_api_helpers import APIException

logger = logging.getLogger(__name__)


class UnsupportedDownloadMethod(APIException):

    def __init__(self):
        super().__init__(status_code=501,
                         message='Unsupported download method',
                         error_id='unsupported_download_method',
                         details={})


class InvalidMetadata(Exception):
    pass


class InvalidNamespaceException(InvalidMetadata):
    pass


class InvalidNameException(InvalidMetadata):
    pass


class GitDownloader(object):

    def __init__(self, download_dir):
        self._download_dir = download_dir

    def download(self, url):
        filename = os.path.join(self._download_dir, str(uuid.uuid4()))
        cmd = ['git', 'clone', '--depth', '1', url, filename]

        with subprocess.Popen(cmd, stderr=subprocess.PIPE) as proc:
            error_msg = proc.stderr.read().decode('utf-8')

        if proc.returncode:
            logger.error('failed to clone: %s', error_msg)
            logger.debug('failed git command: %s', ' '.join(cmd))
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


class DebianFileGenerator(object):

    _debian_dir = 'DEBIAN'
    _generated_files = ['control', 'postinst', 'prerm']
    _generated_files_mod = {'postinst': 0o755, 'prerm': 0o755}

    def __init__(self, config):
        loader = jinja2.FileSystemLoader(config['template_dir'])
        self._env = jinja2.Environment(loader=loader)
        self._control_template = config['control_template']
        self._postint_template = config['postinst_template']
        self._prerm_template = config['prerm_template']
        self._template_files = {'control': config['control_template'],
                                'postinst': config['postinst_template'],
                                'prerm': config['prerm_template']}

    def generate(self, ctx):
        ctx = self._make_template_ctx(ctx)
        ctx = self._make_debian_dir(ctx)
        for filename in self._generated_files:
            ctx = self._generate_file(ctx, filename)
        return ctx

    def _make_template_ctx(self, ctx):
        installed_rules_path = os.path.join(ctx.destination_plugin_path, ctx.installer_base_filename)
        template_context = dict(ctx.metadata, rules_path=installed_rules_path)
        return ctx.with_template_context(template_context)

    def _make_debian_dir(self, ctx):
        debian_dir = os.path.join(ctx.pkgdir, self._debian_dir)
        os.mkdir(debian_dir)
        return ctx.with_debian_dir(debian_dir)

    def _generate_file(self, ctx, filename):
        file_path = os.path.join(ctx.debian_dir, filename)
        template = self._env.get_template(self._template_files[filename])
        with open(file_path, 'w') as f:
            f.write(template.render(ctx.template_context))

        mod = self._generated_files_mod.get(filename)
        if mod:
            os.chmod(file_path, mod)

        return ctx


class PluginService(object):

    def __init__(self, config, worker):
        download_dir = config['download_dir']
        self._build_dir = config['build_dir']
        self._deb_file = '{}.deb'.format(self._build_dir)
        self._config = config
        self._worker = worker
        self._debian_file_generator = DebianFileGenerator(config)

        self._downloaders = {
            'git': GitDownloader(download_dir),
        }
        self._undefined_downloader = UndefinedDownloader(download_dir)

    def _exec(self, ctx, *args, **kwargs):
        ctx.log_debug('Popen(%s, %s)', args, kwargs)
        return subprocess.Popen(*args, **kwargs).wait()

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

    def move(self, ctx):
        ctx.log_debug('moving %s to %s', ctx.extract_path, ctx.plugin_path)
        shutil.rmtree(ctx.plugin_path, ignore_errors=True)
        shutil.move(ctx.extract_path, ctx.plugin_path)
        return ctx
