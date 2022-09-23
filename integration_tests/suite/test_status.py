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

    def setUp(self):
        super().setUpClass()

    def test_status_is_all_ok(self):
        def check_all_ok():
            result = self.plugind.status.get()
            assert_that(
                result,
                has_entries(
                    master_tenant=has_entry('status', 'ok'),
                    rest_api=has_entry('status', 'ok'),
                    service_token=has_entry('status', 'ok'),
                ),
            )

        until.assert_(check_all_ok, tries=10)


class TestStatusWhenWazoAuthDown(BaseIntegrationTest):

    asset = 'plugind_only'

    def setUp(self):
        super().setUpClass()

    def test_status_fail_when_wazo_auth_is_down(self):
        self.restart_service('auth')
        self.restart_service('plugind')
        self.auth = self.make_mock_auth()
        until.true(self.auth.is_up, tries=10)

        self.plugind = self.make_plugind()
        response = until.return_(self.plugind.status.get, timeout=10)
        assert_that(
            response,
            has_entries(
                master_tenant=has_entry('status', 'fail'),
                rest_api=has_entry('status', 'ok'),
                service_token=has_entry('status', 'fail'),
            ),
        )

        self.configure_wazo_auth()

        def _status_all_ok():
            result = self.plugind.status.get()
            assert_that(
                result,
                has_entries(
                    master_tenant=has_entry('status', 'ok'),
                    rest_api=has_entry('status', 'ok'),
                    service_token=has_entry('status', 'ok'),
                ),
            )

        until.assert_(_status_all_ok, tries=10)
