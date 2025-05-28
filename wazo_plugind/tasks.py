# Copyright 2017-2025 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

import logging
import os
import shutil

import yaml
from marshmallow import ValidationError

from . import bus, debian, download, schema
from .context import Context
from .exceptions import (
    CommandExecutionFailed,
    DependencyAlreadyInstalledException,
    PluginAlreadyInstalled,
    PluginValidationException,
)
from .helpers import exec_and_log
from .helpers.validator import Validator

logger = logging.getLogger(__name__)

_publisher = None


class UninstallTask:
    def __init__(self, config, root_worker):
        self._root_worker = root_worker
        self._remover = _PackageRemover(config, root_worker)
        self._publisher = get_publisher(config)
        self._debug_enabled = config['debug']

    def execute(self, ctx):
        return self._uninstall_and_publish(ctx)

    def _uninstall_and_publish(self, ctx):
        try:
            step = 'initializing'
            steps = [
                ('starting', lambda ctx: ctx),
                ('removing', self._remover.remove),
                ('completed', lambda ctx: ctx),
            ]
            for step, fn in steps:
                self._publisher.uninstall(ctx, step)
                ctx = fn(ctx)
        except Exception:
            ctx.log(
                logger.error,
                'Unexpected error while %s',
                step,
                exc_info=self._debug_enabled,
            )
            error_id = f'{step}-error'
            message = f'{step.capitalize()} Error'
            self._publisher.uninstall_error(ctx, error_id, message)


class PackageAndInstallTask:
    def __init__(self, config, root_worker):
        self._root_worker = root_worker
        self._builder = _PackageBuilder(
            config, self._root_worker, self._package_and_install_impl
        )
        self._publisher = get_publisher(config)

    def execute(self, ctx):
        return self._package_and_install_impl(ctx)

    def _package_and_install_impl(self, ctx):
        try:
            step = 'initializing'

            steps = [
                ('starting', lambda ctx: ctx),
                ('downloading', self._builder.download),
                ('extracting', self._builder.extract),
                ('validating', self._builder.validate),
                ('installing dependencies', self._builder.install_dependencies),
                ('building', self._builder.build),
                ('packaging', self._builder.package),
                ('updating', self._builder.update),
                ('installing', self._builder.install),
                ('cleaning', self._builder.clean),
                ('completed', lambda ctx: ctx),
            ]

            for step, fn in steps:
                self._publisher.install(ctx, step)
                ctx = fn(ctx)

        except CommandExecutionFailed as e:
            ctx.log(
                logger.info,
                'an external command failed during the plugin installation: %s',
                e,
            )
            self._builder.clean(ctx)
            details = {'step': step}
            self._publisher.install_error(
                ctx, 'install-error', 'Installation error', details=details
            )
        except PluginAlreadyInstalled:
            ctx.log(
                logger.info,
                '%s/%s is already installed',
                ctx.metadata['namespace'],
                ctx.metadata['name'],
            )
            self._builder.clean(ctx)
            self._publisher.install(ctx, 'completed')
        except PluginValidationException as e:
            ctx.log(logger.info, 'Plugin validation exception %s', e.details)
            details = dict(e.details)
            details['install_options'] = dict(ctx.install_options)
            self._publisher.install_error(ctx, e.error_id, e.message, details=e.details)
        except DependencyAlreadyInstalledException:
            self._builder.clean(ctx)
            self._publisher.install(ctx, 'completed')
        except Exception:
            debug_enabled = ctx.config['debug']
            ctx.log(
                logger.error, 'Unexpected error while %s', step, exc_info=debug_enabled
            )
            error_id = f'{step.replace(" ", "-")}-error'
            message = f'{step.capitalize()} Error'
            details = {'install_options': dict(ctx.install_options)}
            self._publisher.install_error(ctx, error_id, message, details=details)
            self._builder.clean(ctx)


def get_publisher(config):
    global _publisher
    if not _publisher:
        logger.debug('Creating a new publisher...')
        _publisher = bus.Publisher(service_uuid=config['uuid'], **config['bus'])
    return _publisher


class _PackageRemover:
    def __init__(self, config, root_worker):
        self._config = config
        self._root_worker = root_worker

    def remove(self, ctx):
        result = self._root_worker.uninstall(ctx.uuid, ctx.package_name)
        if result is not True:
            raise Exception('Uninstallation failed')
        return ctx


class _PackageBuilder:
    def __init__(self, config, root_worker, package_install_fn):
        self._config = config
        self._downloader = download.Downloader(config)
        self._debian_file_generator = debian.Generator.from_config(config)
        self._root_worker = root_worker
        self._package_install_fn = package_install_fn

    def build(self, ctx):
        namespace, name = ctx.metadata['namespace'], ctx.metadata['name']
        installer_path = os.path.join(
            ctx.extract_path, self._config['default_install_filename']
        )
        ctx.log(logger.debug, 'building %s/%s', namespace, name)
        cmd = [installer_path, 'build']
        self._exec(ctx, cmd, cwd=ctx.extract_path)
        return ctx.with_fields(
            installer_path=installer_path, namespace=namespace, name=name
        )

    def clean(self, ctx):
        extract_path = getattr(ctx, 'extract_path', None)
        if not extract_path:
            return
        ctx.log(logger.debug, 'removing build directory %s', extract_path)
        shutil.rmtree(extract_path)
        return ctx

    def _debianize(self, ctx):
        ctx.log(logger.debug, 'debianizing %s/%s', ctx.namespace, ctx.name)
        ctx = self._debian_file_generator.generate(ctx)
        cmd = ['dpkg-deb', '--build', ctx.pkgdir]
        self._exec(ctx, cmd, cwd=ctx.extract_path)
        deb_path = os.path.join(ctx.extract_path, f'{self._config["build_dir"]}.deb')
        return ctx.with_fields(package_deb_file=deb_path)

    def download(self, ctx):
        return self._downloader.download(ctx)

    def extract(self, ctx):
        extract_path = os.path.join(self._config['extract_dir'], ctx.uuid)
        ctx.log(logger.debug, 'extracting to %s', extract_path)
        shutil.rmtree(extract_path, ignore_errors=True)
        download_path = ctx.download_path
        if subdirectory := ctx.install_options.get('subdirectory'):
            download_path = os.path.join(ctx.download_path, subdirectory)
        shutil.move(download_path, extract_path)
        metadata_filename = os.path.join(
            extract_path, self._config['default_metadata_filename']
        )
        with open(metadata_filename) as f:
            metadata = yaml.safe_load(f)
        return ctx.with_fields(
            metadata=metadata,
            extract_path=extract_path,
        )

    def validate(self, ctx):
        validator = Validator.new_from_config(
            ctx.config, ctx.wazo_version, ctx.install_params
        )
        validator.validate(ctx.metadata)
        ctx.install_params['reinstall'] = False
        return ctx

    def install(self, ctx):
        result = self._root_worker.install(ctx.uuid, ctx.package_deb_file)
        if result is not True:
            raise Exception('Installation failed')
        return ctx

    def install_dependencies(self, ctx):
        dependencies = ctx.metadata.get('depends', [])
        current_wazo_version = ctx.wazo_version
        for dependency in dependencies:
            ctx.log(logger.info, 'installing dependency %s', dependency)
            self.install_dependency(ctx, dependency, current_wazo_version)
        return ctx

    def install_dependency(self, ctx, dep, current_wazo_version):
        try:
            schema.DependencyMetadataSchema().load(dep)
        except ValidationError:
            ctx.log(logger.info, 'invalid dependency %s skipping', dep)
            return

        ctx = Context(
            self._config,
            method='market',
            install_options=dep,
            install_params={'reinstall': False},
            wazo_version=current_wazo_version,
        )
        self._package_install_fn(ctx)

    def update(self, ctx):
        if not ctx.metadata.get('debian_depends'):
            return ctx

        result = self._root_worker.apt_get_update(ctx.uuid)
        if result is not True:
            raise Exception('apt-get update failed')
        return ctx

    def package(self, ctx):
        ctx.log(logger.debug, 'packaging %s/%s', ctx.namespace, ctx.name)
        pkgdir = os.path.join(ctx.extract_path, self._config['build_dir'])
        os.makedirs(pkgdir)
        cmd = ['fakeroot', ctx.installer_path, 'package']
        self._exec(ctx, cmd, cwd=ctx.extract_path, env={**os.environ, 'pkgdir': pkgdir})
        installed_plugin_data_path = os.path.join(
            pkgdir, 'usr/lib/wazo-plugind/plugins', ctx.namespace, ctx.name
        )
        os.makedirs(installed_plugin_data_path)
        plugin_data_path = os.path.join(
            ctx.extract_path, self._config['plugin_data_dir']
        )
        cmd = ['fakeroot', 'cp', '-R', plugin_data_path, installed_plugin_data_path]
        self._exec(ctx, cmd, cwd=ctx.extract_path)
        return self._debianize(ctx.with_fields(pkgdir=pkgdir))

    def _exec(self, ctx, *args, **kwargs):
        log_debug = ctx.get_logger(logger.debug)
        log_error = ctx.get_logger(logger.error)
        exec_and_log(log_debug, log_error, *args, **kwargs)
