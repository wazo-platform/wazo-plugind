# Copyright 2017 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0+

import os
import time
from hamcrest import assert_that, equal_to
import requests
from requests.packages.urllib3.exceptions import InsecureRequestWarning
from xivo_test_helpers.asset_launching_test_case import AssetLaunchingTestCase
from xivo_test_helpers.bus import BusClient

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


class TestServiceDiscoveryWithConsulAndRabbitMQ(BaseIntegrationTest):

    asset = 'service_discovery'

    def test_that_plugind_registers_itself_on_consul(self):
        port = self.service_port(8500, service_name='consul')
        url = 'http://localhost:{}/v1/agent/services'.format(port)

        response = requests.get(url, verify=False)

        services = response.json()
        for service in services.values():
            if service['Service'] == 'wazo-plugind':
                break
        else:
            self.fail('wazo-plugind is not registered: {}'.format(services))

    def test_that_plugind_sends_a_bus_message_when_started(self):
        self.stop_service()
        port = self.service_port(5672, service_name='rabbitmq')
        bus_url = 'amqp://{username}:{password}@{host}:{port}//'.format(username='guest',
                                                                        password='guest',
                                                                        host='localhost',
                                                                        port=port)
        msg_accumulator = BusClient(bus_url).accumulator('service.#')
        msg_accumulator.start_accumulating()

        self.start_service()

        received = self._wait_for_service_started_event(msg_accumulator)
        msg_accumulator.stop_accumulating()
        assert_that(received, equal_to(True), 'The bus message should have been received')

    def _wait_for_service_started_event(self, msg_accumulator):
        for _ in range(10):
            events = msg_accumulator.get_events()
            for event in events:
                if self._is_service_started_event(event):
                    return True
            time.sleep(0.25)
        return False

    @staticmethod
    def _is_service_started_event(event):
        event_name, service_name = event['name'], event['data']['service_name']
        expected = 'service_registered_event', 'wazo-plugind'
        return event_name, service_name == expected
