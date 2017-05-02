# Copyright 2017 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0+

import logging
from flask import Flask, make_response, request
from flask_cors import CORS
from flask_restful import Api, Resource
from pkg_resources import resource_string
from xivo.auth_verifier import AuthVerifier, required_acl
from xivo.rest_api_helpers import APIException, handle_api_exception
from .schema import PluginInstallSchema

logger = logging.getLogger(__name__)


auth_verifier = AuthVerifier()


class _InvalidInstallParamException(APIException):

    def __init__(self, errors):
        super().__init__(status_code=400,
                         message='Invalid data',
                         error_id='invalid_data',
                         resource='plugins',
                         details=self.format_details(errors))

    def format_details(self, errors):
        return {
            field: info[0] if isinstance(info, list) else info
            for field, info in errors.items()
        }


class _BaseResource(Resource):

    method_decorators = [handle_api_exception] + Resource.method_decorators

    @classmethod
    def add_resource(cls, api, *args, **kwargs):
        api.add_resource(cls, cls.api_path)


class _AuthentificatedResource(_BaseResource):

    method_decorators = [auth_verifier.verify_token] + _BaseResource.method_decorators


class Config(_AuthentificatedResource):

    api_path = '/config'
    _config = {}

    @required_acl('plugind.config.read')
    def get(self):
        return {k: v for k, v in self._config.items()}, 200

    @classmethod
    def add_resource(cls, api, config, *args, **kwargs):
        cls._config = config
        super().add_resource(api, *args, **kwargs)


class Plugins(_AuthentificatedResource):

    api_path = '/plugins'

    @required_acl('plugind.plugins.create')
    def post(self):
        body, errors = PluginInstallSchema().load(request.get_json())
        if errors:
            raise _InvalidInstallParamException(errors)

        uuid = self.plugin_service.create(body['url'], body['method'])

        return {'uuid': uuid}

    @classmethod
    def add_resource(cls, api, *args, **kwargs):
        cls.plugin_service = kwargs['plugin_service']
        super().add_resource(api, *args, **kwargs)


class Swagger(_BaseResource):

    api_package = 'wazo_plugind.swagger'
    api_filename = 'api.yml'
    api_path = '/api/api.yml'

    def get(self):
        try:
            api_spec = resource_string(self.api_package, self.api_filename)
        except IOError:
            return {'error': "API spec does not exist"}, 404

        return make_response(api_spec, 200, {'Content-Type': 'application/x-yaml'})


def new_app(config, *args, **kwargs):
    cors_config = config['rest_api']['cors']
    auth_verifier.set_config(config['auth'])
    app = Flask('wazo_plugind')
    app.config.update(config)
    api = Api(app, prefix='/0.1')
    Swagger.add_resource(api, *args, **kwargs)
    Config.add_resource(api, config, *args, **kwargs)
    Plugins.add_resource(api, config, *args, **kwargs)
    if cors_config.pop('enabled', False):
        CORS(app, **cors_config)
    return app
