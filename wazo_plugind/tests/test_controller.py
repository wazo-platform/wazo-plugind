# Copyright 2026 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

from unittest.mock import Mock, patch

import pytest


@pytest.fixture
def controller():
    # imported here: importing wazo_plugind.http at collection time would
    # defeat test_http.py's AuthVerifierFlask patch-before-import
    from wazo_plugind.controller import Controller

    config = {
        'uuid': '00000000-0000-0000-0000-000000000000',
        'rest_api': {
            'listen': '127.0.0.1',
            'port': 9503,
            'certificate': None,
            'private_key': None,
            'cors': {'enabled': False},
        },
        'consul': {},
        'service_discovery': {},
        'bus': {},
        'auth': {},
    }
    with (
        patch('wazo_plugind.controller.AuthClient'),
        patch('wazo_plugind.controller.TokenRenewer'),
        patch('wazo_plugind.controller.Publisher'),
        patch('wazo_plugind.controller.service'),
        patch('wazo_plugind.controller.http'),
        patch('wazo_plugind.controller.http_helpers'),
        patch('wazo_plugind.controller.ServiceCatalogRegistration'),
        patch('wazo_plugind.controller.wsgi'),
    ):
        yield Controller(config, Mock())


def test_stop_before_run_does_not_raise_and_sets_the_tombstone(controller):
    controller.stop('TEST')

    controller._stopping_thread.join(timeout=5)
    assert controller._stopped.is_set()


def test_run_after_stop_does_not_start_the_server(controller):
    controller.stop('TEST')
    controller.run()

    controller._stopping_thread.join(timeout=5)
    controller._server.start.assert_not_called()


def test_stop_after_run_stops_the_server(controller):
    controller.run()
    controller.stop('TEST')

    controller._stopping_thread.join(timeout=5)
    controller._server.stop.assert_called_once_with()
