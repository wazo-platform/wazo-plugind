# Copyright 2017-2020 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

from hamcrest import (
    assert_that,
    calling,
    has_property,
    not_,
)
from requests import HTTPError
from xivo_test_helpers.hamcrest.raises import raises
from xivo_test_helpers import until
from .helpers.base import BaseIntegrationTest, TOKEN_SUB_TENANT


class TestTenantRestriction(BaseIntegrationTest):

    asset = 'plugind_only'

    def _assert_unauthorized(self, url, *args):
        assert_that(
            calling(url).with_args(*args),
            raises(HTTPError).matching(
                has_property('response', has_property('status_code', 401))
            ),
        )

    def test_restrict_only_master_tenant(self):
        plugind = self.get_client(token=TOKEN_SUB_TENANT)

        url = plugind.market.get
        self._assert_unauthorized(url, 'official', 'admin-ui-conference')

        url = plugind.market.list
        self._assert_unauthorized(url)

        url = plugind.plugins.get
        self._assert_unauthorized(url, 'official', 'admin-ui-conference')

        url = plugind.plugins.list
        self._assert_unauthorized(url)

        url = plugind.plugins.install
        self._assert_unauthorized(url)

        url = plugind.plugins.uninstall
        self._assert_unauthorized(url, 'markettests', 'foobar')

        url = plugind.config.get
        self._assert_unauthorized(url)

    def test_503_when_no_auth(self):
        self.stop_service('plugind')
        self.stop_service('auth')
        self.start_service('plugind')

        def _plugind_returns_503():
            assert_that(
                calling(self.list_plugins),
                raises(HTTPError).matching(
                    has_property('response', has_property('status_code', 503))
                ),
            )

        until.assert_(_plugind_returns_503, tries=10)

        self.start_service('auth')

        def _plugind_does_not_return_503():
            assert_that(
                calling(self.list_plugins),
                not_(raises(HTTPError)),
            )

        until.assert_(_plugind_does_not_return_503, tries=10)
