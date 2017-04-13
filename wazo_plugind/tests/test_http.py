# Copyright 2017 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0+

from unittest import TestCase
from functools import wraps
import json
from hamcrest import assert_that, equal_to
from mock import Mock, patch

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


class TestPlugins(TestCase):

    def setUp(self):
        config = {'rest_api': {'cors': {'enabled': False}},
                  'auth': {'host': 'foobar'}}
        self.plugin_service = Mock(PluginService)
        self.app = new_app(config, plugin_service=self.plugin_service).test_client()

    def test_that_missing_fields_return_a_400(self):
        bodies = [
            None,
            {'namespace': 'ns'},
            {'name': 'n'},
        ]

        for body in bodies:
            status_code, _= self.post(body)
            assert_that(status_code, equal_to(400))

    def test_on_succes_returns_result_from_service(self):
        namespace, name, url, method = 'ns', 'n', 'u', 'm'
        body = {
            'namespace': namespace,
            'name': name,
            'url': url,
            'method': method,
        }
        expected = self.plugin_service.create.return_value = {'foo': 'bar'}

        status_code, data = self.post(body)

        assert_that(status_code, equal_to(200))
        assert_that(data, equal_to(expected))
        self.plugin_service.create.assert_called_once_with(namespace, name, url, method)

    def post(self, body):
        result = self.app.post('/0.1/plugins',
                               data=json.dumps(body),
                               headers={'content-type': 'application/json'})
        return result.status_code, json.loads(result.data.decode(encoding='utf-8'))
