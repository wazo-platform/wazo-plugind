# Copyright 2017-2022 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

import logging
import requests
import yaml

from flask import Flask, make_response, request
from flask_cors import CORS
from flask_restful import Api, Resource
from marshmallow import ValidationError
from pkg_resources import resource_string
from xivo import http_helpers
from xivo.http_helpers import add_logger, reverse_proxy_fix_api_spec
from xivo.auth_verifier import AuthVerifier, required_acl, required_tenant
from xivo.rest_api_helpers import handle_api_exception
from xivo.status import Status
from werkzeug.local import LocalProxy as Proxy

from .schema import (
    MarketListRequestSchema,
    MarketListResultSchema,
    PluginInstallQueryStringSchema,
    PluginInstallSchema,
)
from .exceptions import (
    InvalidInstallParamException,
    InvalidInstallQueryStringException,
    InvalidListParamException,
    MarketNotFoundException,
    NotInitializedException,
)

logger = logging.getLogger(__name__)
auth_verifier = AuthVerifier()


_status_aggregator = None


class MasterTenant:
    def __init__(self):
        self._app = None

    def init_app(self, app):
        self._app = app

    def init_value(self, token):
        tenant_uuid = token['metadata']['tenant_uuid']
        self._app.config['auth']['master_tenant_uuid'] = tenant_uuid

    def get_uuid(self):
        if not self._app:
            raise Exception('Flask application not configured')

        tenant_uuid = self._app.config['auth'].get('master_tenant_uuid')
        if not tenant_uuid:
            raise NotInitializedException()
        return tenant_uuid

    def provide_status(self, status):
        status['master_tenant']['status'] = (
            Status.ok
            if self._app.config['auth'].get('master_tenant_uuid')
            else Status.fail
        )


master_tenant = MasterTenant()
master_tenant_uuid = Proxy(master_tenant.get_uuid)


def required_master_tenant():
    return required_tenant(master_tenant_uuid)


class _BaseResource(Resource):

    method_decorators = [handle_api_exception] + Resource.method_decorators

    @classmethod
    def add_resource(cls, api, *args, **kwargs):
        endpoint_prefix = kwargs.get('endpoint_prefix', '')
        endpoint = ''.join([endpoint_prefix, cls.__name__])
        api.add_resource(cls, cls.api_path, endpoint=endpoint)


class _AuthentificatedResource(_BaseResource):

    method_decorators = [
        auth_verifier.verify_token,
        auth_verifier.verify_tenant,
    ] + _BaseResource.method_decorators


class Config(_AuthentificatedResource):

    api_path = '/config'
    _config = {}

    @required_master_tenant()
    @required_acl('plugind.config.read')
    def get(self):
        return {k: v for k, v in self._config.items()}, 200

    @classmethod
    def add_resource(cls, api, config, *args, **kwargs):
        cls._config = config
        super().add_resource(api, *args, **kwargs)


class Market(_AuthentificatedResource):

    api_path = '/market'

    @required_master_tenant()
    @required_acl('plugind.market.read')
    def get(self):
        try:
            list_params = MarketListRequestSchema().load(request.args)
        except ValidationError as e:
            raise InvalidListParamException(e.messages)

        for key, value in request.args.items():
            if key in list_params:
                continue
            list_params[key] = value

        market_proxy = self.plugin_service.new_market_proxy()
        try:
            plugin_list = self.plugin_service.list_from_market(
                market_proxy, **list_params
            )
        except requests.exceptions.ConnectionError:
            raise MarketNotFoundException
        items = MarketListResultSchema().load(plugin_list, many=True)
        return {
            'items': items,
            'total': self.plugin_service.count_from_market(market_proxy, **list_params),
            'filtered': self.plugin_service.count_from_market(
                market_proxy, filtered=True, **list_params
            ),
        }

    @classmethod
    def add_resource(cls, api, *args, **kwargs):
        cls.plugin_service = kwargs['plugin_service']
        super().add_resource(api, *args, **kwargs)


class MarketItem(_AuthentificatedResource):

    api_path = '/market/<namespace>/<name>'

    @required_master_tenant()
    @required_acl('plugind.market.read')
    def get(self, namespace, name):
        market_proxy = self.plugin_service.new_market_proxy()
        return self.plugin_service.get_from_market(market_proxy, namespace, name)

    @classmethod
    def add_resource(cls, api, *args, **kwargs):
        cls.plugin_service = kwargs['plugin_service']
        super().add_resource(api, *args, **kwargs)


class Plugins(_AuthentificatedResource):

    api_path = '/plugins'

    @required_master_tenant()
    @required_acl('plugind.plugins.read')
    def get(self):
        return {
            'items': self.plugin_service.list_(),
            'total': self.plugin_service.count(),
        }

    @required_master_tenant()
    @required_acl('plugind.plugins.create')
    def post(self):
        try:
            body = PluginInstallSchema().load(request.get_json())
        except ValidationError as e:
            raise InvalidInstallParamException(e.messages)

        try:
            params = PluginInstallQueryStringSchema().load(request.args)
        except ValidationError as e:
            raise InvalidInstallQueryStringException(e.messages)

        uuid = self.plugin_service.create(body['method'], params, body['options'])

        return dict(uuid=uuid)

    @classmethod
    def add_resource(cls, api, *args, **kwargs):
        cls.plugin_service = kwargs['plugin_service']
        super().add_resource(api, *args, **kwargs)


class PluginsItem(_AuthentificatedResource):

    api_path = '/plugins/<namespace>/<name>'

    @required_master_tenant()
    @required_acl('plugind.plugins.{namespace}.{name}.delete')
    def delete(self, namespace, name):
        uuid = self.plugin_service.delete(namespace, name)
        return {'uuid': uuid}

    @required_master_tenant()
    @required_acl('plugind.plugins.{namespace}.{name}.read')
    def get(self, namespace, name):
        plugin_metadata = self.plugin_service.get_plugin_metadata(namespace, name)
        return plugin_metadata

    @classmethod
    def add_resource(cls, api, *args, **kwargs):
        cls.plugin_service = kwargs['plugin_service']
        super().add_resource(api, *args, **kwargs)


class StatusChecker(_AuthentificatedResource):

    api_path = '/status'

    @required_acl('plugind.status.read')
    def get(
        self,
    ):
        global _status_aggregator
        return _status_aggregator.status(), 200


class Swagger(_BaseResource):

    api_package = 'wazo_plugind.swagger'
    api_filename = 'api.yml'
    api_path = '/api/api.yml'

    def get(self):
        try:
            api_spec = yaml.load(resource_string(self.api_package, self.api_filename))
        except IOError:
            return {'error': "API spec does not exist"}, 404

        reverse_proxy_fix_api_spec(api_spec)
        response = yaml.dump(dict(api_spec))
        return make_response(response, 200, {'Content-Type': 'application/x-yaml'})


class PlugindAPI:
    def __init__(self, app, config, prefix, decorators=None, *args, **kwargs):
        self._config = config
        self._prefix = prefix
        self._restful_api = Api(app, prefix=self._prefix, decorators=(decorators or []))
        self._args = args
        self._kwargs = kwargs

    def add_resource(self, resource):
        logger.debug('Adding %s to %s %s', resource, self._prefix, self._restful_api)
        resource.add_resource(
            self._restful_api, self._config, *self._args, **self._kwargs
        )


class MultiAPI:
    def __init__(self, *apis):
        self._apis = apis

    def add_resource(self, resource):
        for api in self._apis:
            if api:
                api.add_resource(resource)


def new_app(config, *args, **kwargs):
    cors_config = config['rest_api']['cors']
    auth_verifier.set_config(config['auth'])
    app = Flask('wazo_plugind')
    add_logger(app, logger)
    app.config.update(config)
    app.after_request(http_helpers.log_request)
    master_tenant.init_app(app)

    APIv02 = PlugindAPI(
        app, config, prefix='/0.2', *args, endpoint_prefix='v02', **kwargs
    )
    MultiAPI(APIv02).add_resource(Swagger)
    MultiAPI(APIv02).add_resource(Config)
    MultiAPI(APIv02).add_resource(Market)
    MultiAPI(APIv02).add_resource(MarketItem)
    MultiAPI(APIv02).add_resource(PluginsItem)
    MultiAPI(APIv02).add_resource(Plugins)
    MultiAPI(APIv02).add_resource(StatusChecker)

    if cors_config.pop('enabled', False):
        CORS(app, **cors_config)
    return app


def _update_status_aggregator(status_aggregator):
    global _status_aggregator
    _status_aggregator = status_aggregator
    _status_aggregator.add_provider(provide_status)
    _status_aggregator.add_provider(master_tenant.provide_status)


def provide_status(status):
    status['rest_api']['status'] = Status.ok
