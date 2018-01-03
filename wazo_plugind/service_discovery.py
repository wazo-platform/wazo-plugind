# Copyright 2017 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0+

import requests


def self_check(port, certificate):
    url = 'https://localhost:{}/0.1/config'.format(port)
    try:
        return requests.get(url,
                            headers={'accept': 'application/json'},
                            verify=certificate,
                            timeout=1).status_code == 401
    except Exception:
        return False
