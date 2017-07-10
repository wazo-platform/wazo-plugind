# Copyright 2017 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0+

from unittest import TestCase
from hamcrest import assert_that, contains, equal_to, has_entries
from mock import ANY

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

    def test_market_installation_without_version(self):
        url = 'http://the-market-url'
        input_ = {
            'url': url,
            'method': 'market',
            'options': {
                'namespace': 'foo',
                'name': 'bar',
            }
        }

        result, _ = PluginInstallSchema().load(input_)

        expected = {
            'url': url,
            'method': 'market',
            'options': {
                'namespace': 'foo',
                'name': 'bar',
            },
        }
        assert_that(result, equal_to(expected))

    def test_that_an_invalid_method_returns_an_error(self):
        result, errors = PluginInstallSchema().load({'method': 'foobar',
                                                     'url': 'file:///test'})
        assert_that(
            errors,
            has_entries('method', contains(has_entries('constraint', has_entries('choices', ANY)))))
