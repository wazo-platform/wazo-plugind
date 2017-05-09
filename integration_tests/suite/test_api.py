# Copyright 2017 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0+

import os
from xivo_test_helpers.asset_launching_test_case import AssetLaunchingTestCase
from wazo_plugind_client import Client

VALID_TOKEN = 'valid-token'


class BaseIntegrationTest(AssetLaunchingTestCase):

    assets_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'assets'))
    service = 'plugind'

    def get_client(self, token=VALID_TOKEN):
        port = self.service_port(9503)
        return Client('localhost', port=port, token=token, verify_certificate=False)

    def install_plugin(self, url, method, **kwargs):
        client = self.get_client(**kwargs)
        return client.plugins.install(url, method)

    def list_plugins(self, **kwargs):
        client = self.get_client(**kwargs)
        return client.plugins.list()

    def uninstall_plugin(self, namespace, name, **kwargs):
        client = self.get_client(*kwargs)
        return client.plugins.uninstall(namespace, name)
