# Copyright 2017 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

import requests
import pprint

from hamcrest import assert_that, empty

from .test_api import BaseIntegrationTest


class TestDocumentation(BaseIntegrationTest):

    asset = 'documentation'

    def test_documentation_errors(self):
        api_url = 'https://plugind:9503/0.2/api/api.yml'
        self.validate_api(api_url)

    def validate_api(self, url):
        validator_port = self.service_port(8080, 'swagger-validator')
        validator_url = 'http://localhost:{port}/debug'.format(port=validator_port)
        response = requests.get(validator_url, params={'url': url})
        assert_that(response.json(), empty(), pprint.pformat(response.json()))
