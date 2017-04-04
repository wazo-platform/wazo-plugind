# Copyright 2017 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0+

import os
from hamcrest import assert_that, equal_to
import requests
from requests.packages.urllib3.exceptions import InsecureRequestWarning
from xivo_test_helpers.asset_launching_test_case import AssetLaunchingTestCase

requests.packages.urllib3.disable_warnings(InsecureRequestWarning)

ASSET_ROOT = os.path.join(os.path.dirname(__file__), '..', 'assets')


class TestServiceDiscovery(AssetLaunchingTestCase):

    assets_root = ASSET_ROOT
    asset = 'plugind_only'
    service = 'plugind'

    def test_that_plugind_starts_without_consul_and_rabbitmq(self):
        port = self.service_port(9503)
        url = 'https://localhost:{}/0.1/config'.format(port)

        response = requests.get(url, verify=False)

        assert_that(response.status_code, equal_to(200))
