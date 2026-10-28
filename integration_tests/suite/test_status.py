# Copyright 2022-2026 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

from hamcrest import assert_that, has_entries, has_entry
from wazo_test_helpers import until
from wazo_test_helpers.auth import MockCredentials

from .helpers.base import BaseIntegrationTest


class TestStatusAllOk(BaseIntegrationTest):
    asset = 'plugind_only'

    def test_status_is_all_ok(self):
        def check_all_ok():
            result = self.plugind.status.get()
            assert_that(
                result,
                has_entries(
                    master_tenant=has_entry('status', 'ok'),
                    rest_api=has_entry('status', 'ok'),
                ),
            )

        until.assert_(check_all_ok, tries=10)

    def test_status_fail_when_service_credentials_are_rejected(self):
        self.auth.set_invalid_credentials(
            MockCredentials('plugind-service', 'plugind-password')
        )
        self.restart_service('plugind')
        self.reset_clients()

        response = until.return_(self.plugind.status.get, timeout=10)
        assert_that(
            response,
            has_entries(
                master_tenant=has_entry('status', 'fail'),
                rest_api=has_entry('status', 'ok'),
            ),
        )

        self.restart_service('auth')
        self.reset_clients()
        until.true(self.auth.is_up, tries=10)
        self.configure_token()
        self.wait_strategy.wait(self)
