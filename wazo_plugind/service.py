# Copyright 2017 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0+

import logging
from . import db
from .exceptions import PluginNotFoundException
from .helpers import exec_and_log
from .context import Context

logger = logging.getLogger(__name__)


class PluginService(object):

    def __init__(self, config, status_publisher):
        self._build_dir = config['build_dir']
        self._deb_file = '{}.deb'.format(self._build_dir)
        self._config = config
        self._status_publisher = status_publisher
        self._plugin_db = db.PluginDB(config)

    def _exec(self, ctx, *args, **kwargs):
        log_debug = ctx.get_logger(logger.debug)
        log_error = ctx.get_logger(logger.error)
        exec_and_log(log_debug, log_error, *args, **kwargs)

    def count(self):
        return self._plugin_db.count()

    def count_from_market(self, market_proxy, *args, **kwargs):
        market_db = db.MarketDB(market_proxy, self._plugin_db)
        return market_db.count(*args, **kwargs)

    def create(self, url, method, **kwargs):
        from .tasks import package_and_install
        ctx = Context(self._config, url=url, method=method, install_args=kwargs)
        ctx.log(logger.info, 'installing %s...', url)
        package_and_install.apply_async(args=(ctx,))
        return ctx.uuid

    def new_market_proxy(self):
        return db.MarketProxy(self._config['market'])

    def list_(self):
        return self._plugin_db.list_()

    def list_from_market(self, market_proxy, *args, **kwargs):
        market_db = db.MarketDB(market_proxy, self._plugin_db)
        return market_db.list_(*args, **kwargs)

    def delete(self, namespace, name):
        ctx = Context(self._config, namespace=namespace, name=name)
        ctx.log(logger.info, 'uninstalling %s/%s...', namespace, name)
        plugin = self._plugin_db.get_plugin(namespace, name)
        if not plugin.is_installed():
            raise PluginNotFoundException(namespace, name)
        from .tasks import uninstall_and_publish
        ctx = ctx.with_fields(package_name=plugin.debian_package_name)
        uninstall_and_publish.apply_async(args=(ctx,))
        return ctx.uuid
