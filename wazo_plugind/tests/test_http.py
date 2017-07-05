# Copyright 2017 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0+

from unittest import TestCase
from functools import wraps
from uuid import uuid4
import json
from hamcrest import assert_that, equal_to, has_entries
from mock import ANY, Mock, patch

from ..service import PluginService


class AuthVerifierMock(object):

    def set_config(self, *args, **kwargs):
        pass

    def verify_token(self, func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            return func(*args, **kwargs)
        return wrapper


with patch('xivo.auth_verifier.AuthVerifier', AuthVerifierMock):
    from ..http import new_app


class HTTPAppTestCase(TestCase):

    def setUp(self):
        config = {'rest_api': {'cors': {'enabled': False}},
                  'auth': {'host': 'foobar'}}
        self.plugin_service = Mock(PluginService)
        self.app = new_app(config, plugin_service=self.plugin_service).test_client()


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

    def get(self, **kwargs):
        result = self.app.get('/0.1/market',
                              query_string=kwargs,
                              headers={'content-type': 'application/json'})
        return result.status_code, json.loads(result.data.decode(encoding='utf-8'))


class TestPlugins(HTTPAppTestCase):

    def setUp(self):
        config = {'rest_api': {'cors': {'enabled': False}},
                  'auth': {'host': 'foobar'}}
        self.plugin_service = Mock(PluginService)
        self.app = new_app(config, plugin_service=self.plugin_service).test_client()

    def test_that_invalid_values_in_fields_return_a_400(self):
        bodies = [
            {'method': 'git', 'url': ''},
            {'method': '', 'url': 'http://...'},
            {'method': 'git'},
            None,
            {'url': 42, 'method': None}
        ]
        details = [
            {'url': {'constraint_id': 'length',
                     'constraint': {'min': 1, 'max': None},
                     'message': ANY}},
            {'method': {'constraint_id': 'enum',
                        'constraint': {'choices': ['git', 'market']},
                        'message': ANY}},
            {'url': {'constraint_id': 'required',
                     'constraint': 'required',
                     'message': ANY}},
            {'method': {'constraint_id': 'required',
                        'constraint': 'required',
                        'message': ANY}},
            {'method': {'constraint_id': 'required',
                        'constraint': 'required',
                        'message': ANY},
             'url': {'constraint_id': 'required',
                     'constraint': 'required',
                     'message': ANY}},
            {'method': {'constraint_id': 'not_null',
                        'constraint': 'not_null',
                        'message': ANY},
             'url': {'constraint_id': 'type',
                     'constraint': 'string',
                     'message': ANY}},
        ]

        for body, detail in zip(bodies, details):
            status_code, body = self.post(body)
            assert_that(status_code, equal_to(400))
            assert_that(body, has_entries(
                'error_id', 'invalid_data',
                'message', 'Invalid data',
                'resource', 'plugins',
                'details', detail,
            ))

    def test_on_succes_returns_result_from_service(self):
        url, method = 'url', 'git'
        body = {
            'url': url,
            'method': method,
        }
        self.plugin_service.create.return_value = uuid = str(uuid4())

        status_code, data = self.post(body)

        assert_that(status_code, equal_to(200))
        assert_that(data, equal_to({'uuid': uuid}))
        self.plugin_service.create.assert_called_once_with(url, method, ref='master')

    def test_on_succes_returns_result_from_service_with_options(self):
        url, method, branch = 'url', 'git', 'foobar'
        body = {
            'url': url,
            'method': method,
            'options': {'ref': branch},
        }
        self.plugin_service.create.return_value = uuid = str(uuid4())

        status_code, data = self.post(body)

        assert_that(status_code, equal_to(200))
        assert_that(data, equal_to({'uuid': uuid}))
        self.plugin_service.create.assert_called_once_with(url, method, ref=branch)

    def post(self, body):
        result = self.app.post('/0.1/plugins',
                               data=json.dumps(body),
                               headers={'content-type': 'application/json'})
        return result.status_code, json.loads(result.data.decode(encoding='utf-8'))
