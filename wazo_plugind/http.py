# Copyright 2017 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0+

import logging
from flask import make_response
from flask_restful import Resource
from pkg_resources import resource_string

logger = logging.getLogger(__name__)


class Config(Resource):

    api_path = '/config'
    _config = {}

    def get(self):
        # TODO: add an acl
        return {k: v for k, v in self._config.items()}, 200

    @classmethod
    def add_resource(cls, api, config):
        cls._config = config
        api.add_resource(cls, cls.api_path)


class Api(Resource):

    api_package = 'wazo_plugind.swagger'
    api_filename = 'api.yml'
    api_path = '/api/api.yml'

    @classmethod
    def add_resource(cls, api):
        api.add_resource(cls, cls.api_path)

    def get(self):
        try:
            api_spec = resource_string(self.api_package, self.api_filename)
        except IOError:
            return {'error': "API spec does not exist"}, 404

        return make_response(api_spec, 200, {'Content-Type': 'application/x-yaml'})
