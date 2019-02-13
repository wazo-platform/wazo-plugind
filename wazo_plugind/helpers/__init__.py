# Copyright 2017-2018 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

import logging
import os
import subprocess
from xivo.token_renewer import TokenRenewer
from xivo_auth_client import Client as AuthClient
from xivo_confd_client import Client as ConfdClient

from wazo_plugind.exceptions import CommandExecutionFailed

_DEFAULT_PLUGIN_FORMAT_VERSION = 0

logger = logging.getLogger(__name__)


def exec_and_log(stdout_logger, stderr_logger, *args, **kwargs):
    p = subprocess.Popen(*args, stdout=subprocess.PIPE, stderr=subprocess.PIPE, **kwargs)
    out, err = p.communicate()
    cmd = ' '.join(args[0])
    if out:
        stdout_logger('%s\n==== STDOUT ====\n%s==== END ====', cmd, out.decode('utf8'))
    if err:
        stdout_logger('%s\n==== STDERR====\n%s==== END ====', cmd, err.decode('utf8'))
    if p.returncode != 0:
        raise CommandExecutionFailed(args[0], p.returncode)
    return p


class WazoVersionFinder:

    def __init__(self, config):
        self._token = None
        self._config = config
        self._token_renewer = TokenRenewer(AuthClient(**config['auth']))
        self._token_renewer.subscribe_to_token_change(self.set_token)
        self._version = None

    def get_version(self):
        if not self._version:
            self._version = os.getenv('WAZO_VERSION') or self._query_for_version()
        return self._version

    def set_token(self, token):
        self._token = token

    def _query_for_version(self):
        logger.debug('Using the current version from confd')
        with self._token_renewer:
            client = ConfdClient(token=self._token, **self._config['confd'])
            return client.infos()['wazo_version']
