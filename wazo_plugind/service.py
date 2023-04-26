# Copyright 2017-2023 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

import logging
from . import db
from .exceptions import PluginNotFoundException
from .helpers import exec_and_log, WazoVersionFinder
from .context import Context
from .tasks import PackageAndInstallTask, UninstallTask

logger = logging.getLogger(__name__)


class PluginService:
    def __init__(
        self,
        config,
        status_publisher,
        root_worker,
        executor,
        plugin_db,
        wazo_version_finder,
    ):
        self._build_dir = config['build_dir']
        self._deb_file = f'{self._build_dir}.deb'
        self._config = config
        self._status_publisher = status_publisher
        self._plugin_db = plugin_db
        self._root_worker = root_worker
        self._executor = executor
        self._wazo_version_finder = wazo_version_finder

    def _exec(self, ctx, *args, **kwargs):
        log_debug = ctx.get_logger(logger.debug)
        log_error = ctx.get_logger(logger.error)
        exec_and_log(log_debug, log_error, *args, **kwargs)

    def count(self):
        return self._plugin_db.count()

    def count_from_market(self, market_proxy, *args, **kwargs):
        market_db = self._new_market_db(market_proxy)
        return market_db.count(*args, **kwargs)

    def create(self, method, params, options):
        task = PackageAndInstallTask(self._config, self._root_worker)
        wazo_version = self._wazo_version_finder.get_version()
        ctx = Context(
            self._config,
            method=method,
            install_options=options,
            install_params=params,
            wazo_version=wazo_version,
        )
        ctx.log(logger.info, 'installing %s with params %s...', options, params)
        self._executor.submit(task.execute, ctx)
        return ctx.uuid

    def get_plugin_metadata(self, namespace, name):
        plugin = self._plugin_db.get_plugin(namespace, name)
        if not plugin.is_installed():
            raise PluginNotFoundException(namespace, name)
        return plugin.metadata()

    def new_market_proxy(self):
        return db.MarketProxy(self._config['market'])

    def list_(self):
        return self._plugin_db.list_()

    def get_from_market(self, market_proxy, namespace, name):
        market_db = self._new_market_db(market_proxy)
        results = market_db.list_(namespace=namespace, name=name)
        for result in results:
            return result
        raise PluginNotFoundException(namespace, name)

    def list_from_market(self, market_proxy, *args, **kwargs):
        market_db = self._new_market_db(market_proxy)
        return market_db.list_(*args, **kwargs)

    def delete(self, namespace, name):
        ctx = Context(self._config, namespace=namespace, name=name)
        ctx.log(logger.info, 'uninstalling %s/%s...', namespace, name)
        plugin = self._plugin_db.get_plugin(namespace, name)
        if not plugin.is_installed():
            raise PluginNotFoundException(namespace, name)

        task = UninstallTask(self._config, self._root_worker)
        ctx = ctx.with_fields(package_name=plugin.debian_package_name)
        self._executor.submit(task.execute, ctx)
        return ctx.uuid

    def _new_market_db(self, market_proxy):
        current_wazo_version = self._wazo_version_finder.get_version()
        return db.MarketDB(market_proxy, current_wazo_version, self._plugin_db)

    @classmethod
    def from_config(cls, config, *args, **kwargs):
        kwargs['plugin_db'] = db.PluginDB(config)
        kwargs['wazo_version_finder'] = WazoVersionFinder(config)
        return cls(config, *args, **kwargs)
