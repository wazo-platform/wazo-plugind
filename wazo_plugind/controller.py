# Copyright 2017-2024 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

import logging
import signal
import threading
from concurrent.futures import ThreadPoolExecutor
from functools import partial

from wazo_auth_client import Client as AuthClient
from werkzeug.middleware.proxy_fix import ProxyFix
from xivo import http_helpers, wsgi
from xivo.consul_helpers import ServiceCatalogRegistration
from xivo.http_helpers import ReverseProxied
from xivo.status import StatusAggregator
from xivo.token_renewer import TokenRenewer

from wazo_plugind import http, service
from wazo_plugind.bus import Publisher

from .service_discovery import self_check

logger = logging.getLogger(__name__)


def _signal_handler(controller, signum, frame):
    controller.stop(reason=signal.Signals(signum).name)


class Controller:
    def __init__(self, config, root_worker):
        self._executor = ThreadPoolExecutor(max_workers=10)  # Make it configurable
        self._xivo_uuid = config.get('uuid')
        self._listen_addr = config['rest_api']['listen']
        self._listen_port = config['rest_api']['port']
        self._cors_config = config['rest_api']['cors']
        self._ssl_cert_file = config['rest_api']['certificate']
        ssl_key_file = config['rest_api']['private_key']
        self._consul_config = config['consul']
        self._service_discovery_config = config['service_discovery']
        self._bus_config = config['bus']
        self._token_renewer = TokenRenewer(AuthClient(**config['auth']))
        self._status_aggregator = StatusAggregator()

        bind_addr = (self._listen_addr, self._listen_port)
        self._publisher = Publisher.from_config(config['uuid'], config['bus'])
        plugin_service = service.PluginService.from_config(
            config, self._publisher, root_worker, self._executor
        )

        flask_app = http.new_app(
            config,
            plugin_service=plugin_service,
            status_aggregator=self._status_aggregator,
        )
        if self._ssl_cert_file and ssl_key_file:
            logger.warning(
                'Using service SSL configuration is deprecated. Please use NGINX instead.'
            )
            wsgi.WSGIServer.ssl_adapter = http_helpers.ssl_adapter(
                self._ssl_cert_file, ssl_key_file
            )
        wsgi_app = ReverseProxied(
            ProxyFix(wsgi.WSGIPathInfoDispatcher({'/': flask_app}))
        )
        self._server = wsgi.WSGIServer(bind_addr=bind_addr, wsgi_app=wsgi_app)
        for route in http_helpers.list_routes(flask_app):
            logger.debug(route)

        if not flask_app.config['auth'].get('master_tenant_uuid'):
            self._token_renewer.subscribe_to_next_token_details_change(
                http.master_tenant.init_value
            )
        self._token_renewer.subscribe_to_next_token_details_change(
            lambda t: self._token_renewer.emit_stop()
        )
        self._status_aggregator.add_provider(http.provide_status)
        self._status_aggregator.add_provider(http.master_tenant.provide_status)

    def run(self):
        logger.debug('starting http server')
        signal.signal(signal.SIGTERM, partial(_signal_handler, self))
        signal.signal(signal.SIGINT, partial(_signal_handler, self))

        with ServiceCatalogRegistration(
            'wazo-plugind',
            self._xivo_uuid,
            self._consul_config,
            self._service_discovery_config,
            self._bus_config,
            partial(self_check, self._listen_port),
        ):
            with self._token_renewer:
                try:
                    self._server.start()
                finally:
                    if self._stopping_thread:
                        self._stopping_thread.join()
        self._executor.shutdown()

    def stop(self, reason):
        logger.warning('Stopping wazo-plugind: %s', reason)
        self._stopping_thread = threading.Thread(target=self._server.stop, name=reason)
        self._stopping_thread.start()
