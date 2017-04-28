# -*- coding: utf-8 -*-
# Copyright 2017 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0+

import requests
import pprint

from hamcrest import assert_that, empty

from .test_api import BaseIntegrationTest


class TestDocumentation(BaseIntegrationTest):

    asset = 'documentation'

    def test_documentation_errors(self):
        api_url = 'https://plugind:9503/0.1/api/api.yml'
        self.validate_api(api_url)

    def validate_api(self, url):
        validator_url = u'http://localhost:18080/debug'
        response = requests.get(validator_url, params={'url': url})
        assert_that(response.json(), empty(), pprint.pformat(response.json()))
