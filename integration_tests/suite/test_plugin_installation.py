# Copyright 2017 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0+

import os
from wazo_plugind_client import Client
from hamcrest import assert_that, equal_to, has_entries
from .test_api import BaseIntegrationTest

VALID_TOKEN = 'valid-token'


class TestPluginInstallation(BaseIntegrationTest):

    asset = 'plugind_only'

    def test_when_it_works(self):
        self.remove_from_asset('/tmp/build_success')
        self.remove_from_asset('/tmp/install_success')
        self.remove_from_asset('/tmp/install_failed')

        result = self.install_plugin(url='/tmp/repo', method='git')

        build_success_exists = self.exists_in_asset('tmp/build_success')
        install_success_exists = self.exists_in_asset('tmp/install_success')
        install_failed_exists = self.exists_in_asset('tmp/install_failed')

        assert_that(result, has_entries(namespace='plugind-tests', name='foobar'))
        assert_that(build_success_exists, 'build_success was not created or copied')
        assert_that(install_success_exists, 'install_success was not created')
        assert_that(install_failed_exists, equal_to(False), 'install_failed should not exists')

    def install_plugin(self, url, method):
        port = self.service_port(9503)
        client = Client('localhost', port=port, token=VALID_TOKEN, verify_certificate=False)
        return client.plugins.install(url, method)

    def exists_in_asset(self, path):
        complete_path = self.path_in_asset(path)
        return os.path.exists(complete_path)

    def remove_from_asset(self, path):
        complete_path = self.path_in_asset(path)
        try:
            os.unlink(complete_path)
        except OSError:
            return

    def path_in_asset(self, path):
        return os.path.join(self.assets_root, self.asset, path)
