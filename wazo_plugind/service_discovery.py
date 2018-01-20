# Copyright 2017-2018 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0+

import requests


def self_check(port):
    url = 'https://localhost:{}/0.2/config'.format(port)
    try:
        return requests.get(url,
                            headers={'accept': 'application/json'},
                            verify=False,
                            timeout=1).status_code == 401
    except Exception:
        return False
