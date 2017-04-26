# Copyright 2017 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0+

from wazo_plugind_client import Client
from hamcrest import assert_that, has_entries
from .test_api import BaseIntegrationTest

VALID_TOKEN = 'valid-token'


class TestPluginInstallation(BaseIntegrationTest):

    asset = 'plugind_only'

    def test_when_it_works(self):
        result = self.install_plugin(url='/tmp/repo', method='git')

        assert_that(result, has_entries(namespace='plugind-tests', name='foobar'))

    def install_plugin(self, url, method):
        port = self.service_port(9503)
        client = Client('localhost', port=port, token=VALID_TOKEN, verify_certificate=False)
        return client.plugins.install(url, method)
