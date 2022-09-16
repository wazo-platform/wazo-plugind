# Copyright 2022 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

from hamcrest import (
    assert_that,
    has_entries,
    has_entry,
)
from wazo_test_helpers import until
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
        response = until.return_(plugind_client.status.get, timeout=5)
        assert_that(
            response,
            has_entries(
                master_tenant=has_entry('status', 'fail'),
                rest_api=has_entry('status', 'ok'),
                service_token=has_entry('status', 'fail'),
            ),
        )
        self.start_service('auth')

        def _until_plugind_status_is_all_ok():
            response = plugind_client.status.get()
            assert_that(
                response,
                has_entries(
                    master_tenant=has_entry('status', 'ok'),
                    rest_api=has_entry('status', 'ok'),
                    service_token=has_entry('status', 'ok'),
                ),
            )

        until.assert_(_until_plugind_status_is_all_ok, tries=10)
