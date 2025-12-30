# Copyright 2017-2025 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

import requests

from .helpers.base import TOKEN, BaseIntegrationTest


class TestHTTPInterface(BaseIntegrationTest):
    asset = 'plugind_only'

    def test_that_a_request_with_empty_body_returns_400(self):
        port = self.service_port(9503, 'plugind')
        url = f'http://127.0.0.1:{port}/0.2/plugins'
        headers = {
            'X-Auth-Token': TOKEN,
        }

        response = requests.post(url, headers=headers, data='')

        assert response.status_code == 400
