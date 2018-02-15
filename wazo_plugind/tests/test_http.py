# Copyright 2017-2018 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0+

import json

from functools import wraps
from hamcrest import assert_that, equal_to, has_entries
from mock import ANY, Mock, patch, sentinel
from unittest import TestCase

from ..exceptions import PluginNotFoundException
from ..service import PluginService

API_VERSION = '0.2'


class AuthVerifierMock:

    def set_config(self, *args, **kwargs):
        pass

    def verify_token(self, func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            return func(*args, **kwargs)
        return wrapper


with patch('xivo.auth_verifier.AuthVerifier', AuthVerifierMock):
    from ..http import new_app, MultiAPI, PlugindAPI


class HTTPAppTestCase(TestCase):

    def setUp(self):
        config = {'rest_api': {'cors': {'enabled': False}},
                  'auth': {'host': 'foobar'}}
        self.plugin_service = Mock(PluginService)
        self.plugin_service.create.return_value = {'create': 'return_value'}
        self.app = new_app(config, plugin_service=self.plugin_service).test_client()

    def get_plugin(self, namespace, name, version=API_VERSION):
        url = '/{version}/plugins/{namespace}/{name}'.format(version=version, namespace=namespace, name=name)
        result = self.app.get(url)
        return result.status_code, json.loads(result.data.decode(encoding='utf-8'))

    def post(self, body, version=API_VERSION):
        result = self.app.post('/{}/plugins'.format(version),
                               data=json.dumps(body),
                               headers={'content-type': 'application/json'})
        return result.status_code, json.loads(result.data.decode(encoding='utf-8'))


class TestMarket(HTTPAppTestCase):

    def test_that_get_returns_results_from_the_service(self):
        self.plugin_service.count_from_market.return_value = 0
        self.plugin_service.list_from_market.return_value = []

        status_code, body = self.get()

        expected = {'total': self.plugin_service.count_from_market.return_value,
                    'filtered': self.plugin_service.count_from_market.return_value,
                    'items': self.plugin_service.list_from_market.return_value}
        assert_that(body, equal_to(expected))
        assert_that(status_code, equal_to(200))

    def test_errors_on_invalid_limit(self):
        self.plugin_service.count_from_market.return_value = 0
        self.plugin_service.list_from_market.return_value = []

        status_code, body = self.get(limit=-1)

        assert_that(status_code, equal_to(400))

    def test_that_extra_fields_are_used(self):
        self.plugin_service.list_from_market.return_value = []
        self.plugin_service.count_from_market.return_value = 0

        status_code, body = self.get(namespace='foobar')

        self.plugin_service.list_from_market.assert_called_once_with(
            ANY, namespace='foobar', direction=ANY, limit=ANY, offset=ANY, order=ANY, search=ANY)

    def test_get_by_namespace_and_name(self):
        self.plugin_service.get_from_market.side_effect = PluginNotFoundException('namespace', 'name')

        status_code, response = self.get('namespace', 'name')

        assert_that(status_code, equal_to(404))

    def get(self, *args, **kwargs):
        base_url = '/0.2/market'
        headers = {'content-type': 'application/json'}

        if args:
            url = '{}/{}/{}'.format(base_url, *args)
        else:
            url = base_url

        result = self.app.get(url, query_string=kwargs, headers=headers)
        return result.status_code, json.loads(result.data.decode(encoding='utf-8'))


class TestPlugins(HTTPAppTestCase):

    def test_get_plugin(self):
        self.plugin_service.get_plugin_metadata.return_value = {'meta': 'data'}
        status_code, response = self.get_plugin('namespace', 'name')

        assert_that(status_code, equal_to(200))
        assert_that(response, equal_to(self.plugin_service.get_plugin_metadata.return_value))

    def test_get_plugin_not_found(self):
        self.plugin_service.get_plugin_metadata.side_effect = PluginNotFoundException('namespace', 'name')

        status_code, response = self.get_plugin('namespace', 'name')

        assert_that(status_code, equal_to(404))

    def test_install_with_no_method(self):
        status_code, response = self.post({'options': {'url': 'http://'}})

        assert_that(status_code, equal_to(400))
        assert_that(response, has_entries('error_id', 'invalid_data',
                                          'message', 'Invalid data',
                                          'resource', 'plugins',
                                          'details', {'method': {'constraint_id': 'required',
                                                                 'constraint': 'required',
                                                                 'message': ANY}}))

    def test_install_with_an_unknown_method(self):
        status_code, response = self.post({'method': 'svn', 'options': {'url': 'http://'}})

        assert_that(status_code, equal_to(400))
        assert_that(response, has_entries('error_id', 'invalid_data',
                                          'message', 'Invalid data',
                                          'resource', 'plugins',
                                          'details', {'method': {'constraint_id': 'enum',
                                                                 'constraint': {'choices': ['git', 'market']},
                                                                 'message': ANY}}))

    def test_market_install_with_minimal_arguments(self):
        options = {'name': 'foo', 'namespace': 'bar'}
        self.post({'method': 'market', 'options': options})

        self.plugin_service.create.assert_called_once_with('market', {'reinstall': False}, options)

    def test_market_install_with_all_arguments(self):
        options = {'name': 'foo', 'namespace': 'bar', 'version': '0.0.1'}
        self.post({'method': 'market', 'options': options})

        self.plugin_service.create.assert_called_once_with('market', {'reinstall': False}, options)

    def test_market_install_with_no_name_and_namespace(self):
        status_code, response = self.post({'method': 'market', 'options': {}})

        assert_that(status_code, equal_to(400))
        assert_that(
            response,
            has_entries('error_id', 'invalid_data',
                        'message', 'Invalid data',
                        'resource', 'plugins',
                        'details', {'options': {'name': {'constraint_id': 'required',
                                                         'constraint': 'required',
                                                         'message': ANY},
                                                'namespace': {'constraint_id': 'required',
                                                              'constraint': 'required',
                                                              'message': ANY}}}))

    def test_git_install_with_minimal_arguments(self):
        options = {'url': 'http://'}
        self.post({'method': 'git', 'options': options})

        self.plugin_service.create.assert_called_once_with(
            'git',
            {'reinstall': False},
            dict(ref='master', **options),
        )

    def test_git_install_with_a_branch_name(self):
        options = {'url': 'http://', 'ref': 'foobar'}
        self.post({'method': 'git', 'options': options})

        self.plugin_service.create.assert_called_once_with('git', {'reinstall': False}, options)

    def test_git_install_with_no_url(self):
        options = {'ref': 'foobar'}
        status_code, response = self.post({'method': 'git', 'options': options})

        assert_that(status_code, equal_to(400))
        assert_that(
            response,
            has_entries('error_id', 'invalid_data',
                        'message', 'Invalid data',
                        'resource', 'plugins',
                        'details', {'options': {'url': {'constraint_id': 'required',
                                                        'constraint': 'required',
                                                        'message': ANY}}}))


class TestMultiAPI(TestCase):

    def test_given_no_apis_when_add_resource_then_nothing(self):
        multi = MultiAPI()

        multi.add_resource(Mock())

        # no exception raised

    def test_given_two_apis_when_add_resource_then_add_resource_called_on_each_api(self):
        api1, api2 = Mock(), Mock()
        multi = MultiAPI(api1, api2)

        multi.add_resource(sentinel.resource)

        api1.add_resource.assert_called_once_with(sentinel.resource)
        api2.add_resource.assert_called_once_with(sentinel.resource)

    def test_given_one_false_api_when_add_resource_then_add_resource_called_on_each_non_false_api(self):
        api1, api2 = Mock(), Mock()
        multi = MultiAPI(api1, False, api2)

        multi.add_resource(sentinel.resource)

        api1.add_resource.assert_called_once_with(sentinel.resource)
        api2.add_resource.assert_called_once_with(sentinel.resource)


class TestPlugindAPI(TestCase):

    @patch('wazo_plugind.http.Api')
    def test_when_add_resource_then_add_resource_called_with_right_args(self, RestfulApi):
        restful_api = RestfulApi.return_value
        api = PlugindAPI(sentinel.app,
                         sentinel.config,
                         sentinel.prefix,
                         sentinel.decorators,
                         sentinel.args,
                         sentinel=sentinel.kwargs)
        resource = Mock()

        api.add_resource(resource)

        RestfulApi.assert_called_once_with(sentinel.app,
                                           prefix=sentinel.prefix,
                                           decorators=sentinel.decorators)
        resource.add_resource.assert_called_once_with(restful_api,
                                                      sentinel.config,
                                                      sentinel.args,
                                                      sentinel=sentinel.kwargs)
