# Copyright 2017 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0+

import logging
from flask import Flask, make_response, request
from flask_cors import CORS
from flask_restful import Api, Resource
from pkg_resources import resource_string
from xivo.auth_verifier import AuthVerifier, required_acl
from xivo.rest_api_helpers import handle_api_exception
from .schema import MarketListRequestSchema, PluginInstallSchema, PluginInstallSchemaV01
from .exceptions import InvalidInstallParamException, InvalidListParamException

logger = logging.getLogger(__name__)


auth_verifier = AuthVerifier()


class _BaseResource(Resource):

    method_decorators = [handle_api_exception] + Resource.method_decorators

    @classmethod
    def add_resource(cls, api, *args, **kwargs):
        endpoint_prefix = kwargs.get('endpoint_prefix', '')
        endpoint = ''.join([endpoint_prefix, cls.__name__])
        api.add_resource(cls, cls.api_path, endpoint=endpoint)


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


class Market(_AuthentificatedResource):

    api_path = '/market'

    @required_acl('plugind.market.read')
    def get(self):
        list_params, errors = MarketListRequestSchema().load(request.args)
        if errors:
            raise InvalidListParamException(errors)

        for key, value in request.args.items():
            if key in list_params:
                continue
            list_params[key] = value

        market_proxy = self.plugin_service.new_market_proxy()
        return {
            'items': self.plugin_service.list_from_market(market_proxy, **list_params),
            'total': self.plugin_service.count_from_market(market_proxy, **list_params),
            'filtered': self.plugin_service.count_from_market(market_proxy, filtered=True, **list_params)
        }

    @classmethod
    def add_resource(cls, api, *args, **kwargs):
        cls.plugin_service = kwargs['plugin_service']
        super().add_resource(api, *args, **kwargs)


class Plugins(_AuthentificatedResource):

    api_path = '/plugins'

    @required_acl('plugind.plugins.read')
    def get(self):
        return {
            'items': self.plugin_service.list_(),
            'total': self.plugin_service.count(),
        }

    @required_acl('plugind.plugins.create')
    def post(self):
        body, errors = PluginInstallSchema().load(request.get_json())
        if errors:
            raise InvalidInstallParamException(errors)

        method, options = body['method'], body['options']
        return self._post(method, options)

    def _post(self, method, options):
        uuid = self.plugin_service.create(method, **options)

        return {'uuid': uuid}

    @classmethod
    def add_resource(cls, api, *args, **kwargs):
        cls.plugin_service = kwargs['plugin_service']
        super().add_resource(api, *args, **kwargs)


class PluginsV01(Plugins):

    @required_acl('plugind.plugins.create')
    def post(self):
        body, errors = PluginInstallSchemaV01().load(request.get_json())
        if errors:
            raise InvalidInstallParamException(errors)

        method, options = body['method'], body['options']
        url = body.get('url')
        if url:
            options['url'] = url

        return self._post(method, options)


class PluginsItem(_AuthentificatedResource):

    api_path = '/plugins/<namespace>/<name>'

    @required_acl('plugind.plugins.{namespace}.{name}.delete')
    def delete(self, namespace, name):
        uuid = self.plugin_service.delete(namespace, name)
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


def set_api(app, prefix, config, resources, override=None, *args, **kwargs):
    override = override or {}
    api = Api(app, prefix=prefix)
    resources = dict(resources)
    resources.update(override)
    for ResourceClass in resources.values():
        logger.debug('Adding %s to %s %s', ResourceClass, prefix, api)
        ResourceClass.add_resource(api, config, *args, **kwargs)


def new_app(config, *args, **kwargs):
    cors_config = config['rest_api']['cors']
    auth_verifier.set_config(config['auth'])
    app = Flask('wazo_plugind')
    app.config.update(config)

    latest = {'Swagger': Swagger, 'Config': Config, 'Market': Market,
              'Plugins': Plugins, 'PluginsItem': PluginsItem}
    v01 = {'Plugins': PluginsV01}

    set_api(app, '/0.1', config, latest, override=v01, *args, endpoint_prefix='v01', **kwargs)
    set_api(app, '/0.2', config, latest, *args, **kwargs)

    if cors_config.pop('enabled', False):
        CORS(app, **cors_config)
    return app
