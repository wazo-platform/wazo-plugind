# Copyright 2017 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0+

import logging
import signal
import sys
from threading import Thread
from functools import partial
from cheroot import wsgi
from werkzeug.contrib.fixers import ProxyFix
from xivo import http_helpers
from xivo.http_helpers import ReverseProxied
from xivo.consul_helpers import ServiceCatalogRegistration
from wazo_plugind import celery, http, bus, service
from .service_discovery import self_check

logger = logging.getLogger(__name__)


def _signal_handler(signum, frame):
    logger.info('SIGTERM received, terminating')
    sys.exit(0)


class Controller(object):

    def __init__(self, config):
        self._xivo_uuid = config.get('uuid')
        self._listen_addr = config['rest_api']['https']['listen']
        self._listen_port = config['rest_api']['https']['port']
        self._cors_config = config['rest_api']['cors']
        ssl_cert_file = config['rest_api']['https']['certificate']
        ssl_key_file = config['rest_api']['https']['private_key']
        self._consul_config = config['consul']
        self._service_discovery_config = config['service_discovery']
        self._bus_config = config['bus']

        bind_addr = (self._listen_addr, self._listen_port)
        self._publisher = bus.StatusPublisher.from_config(config)
        celery.worker = celery.Worker.from_config(config)
        plugin_service = service.PluginService(config, self._publisher)

        flask_app = http.new_app(config, plugin_service=plugin_service)
        flask_app.after_request(http_helpers.log_request)
        wsgi.WSGIServer.ssl_adapter = http_helpers.ssl_adapter(ssl_cert_file, ssl_key_file)
        wsgi_app = ReverseProxied(ProxyFix(wsgi.WSGIPathInfoDispatcher({'/': flask_app})))
        self._server = wsgi.WSGIServer(bind_addr=bind_addr, wsgi_app=wsgi_app)
        for route in http_helpers.list_routes(flask_app):
            logger.debug(route)

    def run(self):
        logger.debug('starting http server')
        signal.signal(signal.SIGTERM, _signal_handler)
        publisher_thread = Thread(target=self._publisher.run)
        publisher_thread.start()
        celery.worker.run()
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
        self._publisher.stop()
        publisher_thread.join()
