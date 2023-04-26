# Copyright 2017-2023 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

import requests


def self_check(port):
    url = f'http://localhost:{port}/0.2/config'
    try:
        return (
            requests.get(
                url, headers={'accept': 'application/json'}, timeout=1
            ).status_code
            == 401
        )
    except Exception:
        return False
