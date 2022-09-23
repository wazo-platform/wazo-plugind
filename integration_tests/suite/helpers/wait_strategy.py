# Copyright 2022 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later


from hamcrest import assert_that, has_entries

from wazo_test_helpers import until
from wazo_test_helpers.wait_strategy import WaitStrategy


class EverythingOkWaitStrategy(WaitStrategy):
    def wait(self, plugind_client):
        def is_ready():
            status = plugind_client.plugind.status.get()
            assert_that(
                status,
                has_entries(
                    {
                        'master_tenant': has_entries(status='ok'),
                        'rest_api': has_entries(status='ok'),
                        'service_token': has_entries(status='ok'),
                    }
                ),
            )

        until.assert_(is_ready, tries=60)
