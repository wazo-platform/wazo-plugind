# Copyright 2017 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0+

import os
from hamcrest import assert_that, equal_to
import requests
from requests.packages.urllib3.exceptions import InsecureRequestWarning
from xivo_test_helpers.asset_launching_test_case import AssetLaunchingTestCase

requests.packages.urllib3.disable_warnings(InsecureRequestWarning)


class BaseIntegrationTest(AssetLaunchingTestCase):

    assets_root = os.path.join(os.path.dirname(__file__), '..', 'assets')
    service = 'plugind'


class TestServiceDiscoveryNoConsulNoRabbitmq(BaseIntegrationTest):

    asset = 'plugind_only'

    def test_that_plugind_starts_without_consul_and_rabbitmq(self):
        port = self.service_port(9503)
        url = 'https://localhost:{}/0.1/config'.format(port)

        response = requests.get(url, verify=False)

        assert_that(response.status_code, equal_to(200))


class TestServiceDiscoveryWithConsul(BaseIntegrationTest):

    asset = 'service_discovery'

    def test_that_plugind_starts_without_consul(self):
        port = self.service_port(8500, service_name='consul')
        url = 'http://localhost:{}/v1/agent/services'.format(port)

        response = requests.get(url, verify=False)

        services = response.json()
        for service in services.values():
            if service['Service'] == 'wazo-plugind':
                break
        else:
            self.fail('wazo-plugind is not registered: {}'.format(services))
