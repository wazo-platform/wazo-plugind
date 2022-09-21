# Copyright 2022 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

from hamcrest import (
    assert_that,
    calling,
    has_entries,
    has_entry,
)
from requests.exceptions import ConnectionError
from wazo_test_helpers import until
from wazo_test_helpers.hamcrest.raises import raises
from .helpers.base import BaseIntegrationTest


class TestStatusAllOk(BaseIntegrationTest):

    asset = 'plugind_only'

    def test_status_is_all_ok(self):
        plugind_client = self.get_client()
        response = plugind_client.status.get()
        assert_that(
            response,
            has_entries(
                master_tenant=has_entry('status', 'ok'),
                rest_api=has_entry('status', 'ok'),
                service_token=has_entry('status', 'ok'),
            ),
        )


class TestStatusWhenWazoAuthDown(BaseIntegrationTest):

    asset = 'plugind_only'

    def test_status_fail_when_wazo_auth_is_down(self):
        self.stop_service('plugind')
        self.stop_service('auth')
        self.start_service('plugind')
        plugind_client = self.get_client()
        assert_that(
            calling(plugind_client.status.get),
            raises(ConnectionError),
        )
        self.start_service('auth')

        response = until.return_(plugind_client.status.get, timeout=10)
        assert_that(
            response,
            has_entries(
                master_tenant=has_entry('status', 'ok'),
                rest_api=has_entry('status', 'ok'),
                service_token=has_entry('status', 'ok'),
            ),
        )
