# Copyright 2017 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0+

import logging
from cherrypy import wsgiserver
from flask import Flask
from flask_restful import Api
from xivo import http_helpers
from wazo_plugind import http

logger = logging.getLogger(__name__)


class Controller(object):

    def __init__(self, config):
        listen_addr = config['rest_api']['https']['listen']
        listen_port = config['rest_api']['https']['port']
        bind_addr = (listen_addr, listen_port)
        flask_app = self._new_flask_app(config)
        wsgi_app = wsgiserver.WSGIPathInfoDispatcher({'/': flask_app})
        self._server = wsgiserver.CherryPyWSGIServer(bind_addr=bind_addr, wsgi_app=wsgi_app)
        for route in http_helpers.list_routes(flask_app):
            logger.debug(route)

    def run(self):
        logger.debug('starting http server')
        try:
            self._server.start()
        finally:
            self._server.stop()

    def _new_flask_app(self, config):
        app = Flask('wazo_plugind')
        app.config.update(config)
        api = Api(app, prefix='/0.1')
        http.Api.add_resource(api)
        http.Config.add_resource(api, config)
        return app
