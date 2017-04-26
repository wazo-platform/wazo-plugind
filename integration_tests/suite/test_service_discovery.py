# Copyright 2017 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0+

import requests

from hamcrest import all_of
from hamcrest import assert_that
from hamcrest import equal_to
from hamcrest import has_entry
from hamcrest import has_item
from requests.packages.urllib3.exceptions import InsecureRequestWarning
from xivo_test_helpers import until
from xivo_test_helpers.bus import BusClient
from .test_api import BaseIntegrationTest

requests.packages.urllib3.disable_warnings(InsecureRequestWarning)


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

        self.start_service()

        def bus_event_received(accumulator):
            assert_that(accumulator.accumulate(), has_item(all_of(
                has_entry('name', 'service_registered_event'),
                has_entry('data', has_entry('service_name', 'wazo-plugind')))))

        until.assert_(bus_event_received, msg_accumulator, tries=10, interval=0.25, message='The bus message should have been received')
