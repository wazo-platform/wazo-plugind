# Copyright 2017-2020 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

import logging
import signal
import sys
from concurrent.futures import ThreadPoolExecutor
from threading import Thread
from functools import partial
from cheroot import wsgi
from werkzeug.contrib.fixers import ProxyFix
from xivo import http_helpers
from xivo.http_helpers import ReverseProxied
from xivo.consul_helpers import ServiceCatalogRegistration
from wazo_plugind import http, bus, service
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

        bind_addr = (self._listen_addr, self._listen_port)
        self._publisher = bus.StatusPublisher.from_config(config)
        plugin_service = service.PluginService.from_config(
            config, self._publisher, root_worker, self._executor
        )

        flask_app = http.new_app(config, plugin_service=plugin_service)
        flask_app.after_request(http_helpers.log_request)
        wsgi.WSGIServer.ssl_adapter = http_helpers.ssl_adapter(
            self._ssl_cert_file, ssl_key_file
        )
        wsgi_app = ReverseProxied(
            ProxyFix(wsgi.WSGIPathInfoDispatcher({'/': flask_app}))
        )
        self._server = wsgi.WSGIServer(bind_addr=bind_addr, wsgi_app=wsgi_app)
        for route in http_helpers.list_routes(flask_app):
            logger.debug(route)

    def run(self):
        logger.debug('starting http server')
        signal.signal(signal.SIGTERM, _signal_handler)
        publisher_thread = Thread(target=self._publisher.run)
        publisher_thread.start()
        with ServiceCatalogRegistration(
            'wazo-plugind',
            self._xivo_uuid,
            self._consul_config,
            self._service_discovery_config,
            self._bus_config,
            partial(self_check, self._listen_port),
        ):
            try:
                self._server.start()
            except (KeyboardInterrupt, SystemExit):
                logger.info('Main process stopping')
            finally:
                self._server.stop()
        self._executor.shutdown()
        self._publisher.stop()
        publisher_thread.join()
