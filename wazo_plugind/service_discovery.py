# Copyright 2017 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0+

from http import client


def self_check(port):
    conn = client.HTTPSConnection('localhost', port, timeout=1)
    try:
        conn.request('GET', '/0.1/config')
    except (client.HTTPException, ConnectionRefusedError):
        return False
    response = conn.getresponse()
    return response.status == 200
