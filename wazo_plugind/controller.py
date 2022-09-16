# Copyright 2017-2022 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

import logging
import signal
import sys

from cheroot import wsgi
from concurrent.futures import ThreadPoolExecutor
from functools import partial
from wazo_auth_client import Client as AuthClient
from wazo_plugind import http, service
from wazo_plugind.bus import Publisher
from werkzeug.contrib.fixers import ProxyFix
from xivo import http_helpers
from xivo.consul_helpers import ServiceCatalogRegistration
from xivo.status import StatusAggregator, TokenStatus
from xivo.http_helpers import ReverseProxied
from xivo.token_renewer import TokenRenewer

from .service_discovery import self_check

logger = logging.getLogger(__name__)


def _signal_handler(signum, frame):
    logger.info('SIGTERM received, terminating')
    sys.exit(0)


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
        self._token_status = TokenStatus()

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
        self._token_renewer.subscribe_to_token_change(
            self._token_status.token_change_callback
        )
        self._status_aggregator.add_provider(self._token_status.provide_status)
        http._update_status_aggregator(self._status_aggregator)

    def run(self):
        logger.debug('starting http server')
        signal.signal(signal.SIGTERM, _signal_handler)

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
                except (KeyboardInterrupt, SystemExit):
                    logger.info('Main process stopping')
                finally:
                    self._server.stop()
        self._executor.shutdown()
