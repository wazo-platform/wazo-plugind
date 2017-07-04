# Copyright 2017 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0+

from unittest import TestCase
from hamcrest import assert_that, equal_to

from ..schema import PluginInstallSchema


class TestInstallationSchema(TestCase):

    def test_git_installation_without_ref(self):
        url = 'file://my-git-repo.git'
        input_ = dict(
            url=url,
            method='git',
        )

        result, _ = PluginInstallSchema().load(input_)

        expected = {'url': url, 'method': 'git', 'options': {'ref': 'master'}}
        assert_that(result, equal_to(expected))

    def test_git_installation_with_ref(self):
        url = 'file://my-git-repo.git'
        input_ = dict(
            url=url,
            method='git',
            options={'ref': 'v0.0.1'},
        )

        result, _ = PluginInstallSchema().load(input_)

        expected = {'url': url, 'method': 'git', 'options': {'ref': 'v0.0.1'}}
        assert_that(result, equal_to(expected))
