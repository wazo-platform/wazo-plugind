# Copyright 2017 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0+

import logging
import signal
import sys
from functools import partial
from cherrypy import wsgiserver
from xivo import http_helpers
from xivo.consul_helpers import ServiceCatalogRegistration
from wazo_plugind import http, service
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
        # TODO find how its configured using the builtin ssl adapter
        # ssl_ciphers = config['rest_api']['https']['ciphers']
        bind_addr = (self._listen_addr, self._listen_port)
        plugin_service = service.PluginService()
        flask_app = http.new_app(config, plugin_service=plugin_service)
        Adapter = wsgiserver.get_ssl_adapter_class('builtin')
        adapter = Adapter(ssl_cert_file, ssl_key_file)
        wsgiserver.CherryPyWSGIServer.ssl_adapter = adapter
        wsgi_app = wsgiserver.WSGIPathInfoDispatcher({'/': flask_app})
        self._server = wsgiserver.CherryPyWSGIServer(bind_addr=bind_addr, wsgi_app=wsgi_app)
        for route in http_helpers.list_routes(flask_app):
            logger.debug(route)

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
            try:
                self._server.start()
            except KeyboardInterrupt:
                logger.info("Ctrl-C received, terminating")
            finally:
                self._server.stop()
