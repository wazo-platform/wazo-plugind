# Copyright 2017 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0+

import logging
from flask import Flask, make_response, request
from flask_cors import CORS
from flask_restful import Api, Resource
from pkg_resources import resource_string
from xivo.auth_verifier import AuthVerifier, required_acl
from xivo.rest_api_helpers import APIException, handle_api_exception

logger = logging.getLogger(__name__)


auth_verifier = AuthVerifier()


class _MissingFieldError(APIException):

    def __init__(self, *args, **kwargs):
        missing = [field for field, value in kwargs.items() if value is None]
        super().__init__(status_code=400,
                         message='Missing required fields',
                         error_id='missing_required_fields',
                         details={'fields': missing})


class _BaseResource(Resource):

    method_decorators = [auth_verifier.verify_token, handle_api_exception] + Resource.method_decorators

    @classmethod
    def add_resource(cls, api, *args, **kwargs):
        api.add_resource(cls, cls.api_path)


class Config(_BaseResource):

    api_path = '/config'
    _config = {}

    def get(self):
        # TODO: add an acl
        return {k: v for k, v in self._config.items()}, 200

    @classmethod
    def add_resource(cls, api, config, *args, **kwargs):
        cls._config = config
        super().add_resource(api, *args, **kwargs)


class Plugins(_BaseResource):

    api_path = '/plugins'

    @required_acl('plugind.plugins.create')
    def post(self):
        # Add validation on namespace and name to avoid path manipulation
        data = request.get_json() or {}
        namespace, name = data.get('namespace'), data.get('name')
        method, url = data.get('method'), data.get('url')

        if None in (namespace, name, method, url):
            raise _MissingFieldError(namespace=namespace, name=name, method=method, url=url)

        return self.plugin_service.create(namespace, name, url, method)

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
