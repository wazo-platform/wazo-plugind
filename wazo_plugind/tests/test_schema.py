# Copyright 2017 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0+

from unittest import TestCase
from hamcrest import assert_that, contains, equal_to, has_entries, all_of, has_key
from mock import ANY

from ..schema import MarketListResultSchema, PluginInstallSchemaV01, PluginInstallSchema


class TestMarketResultSchema(TestCase):

    def test_that_install_options_are_removed(self):
        plugin_info = {
            'name': 'foo',
            'namespace': 'foobar',
            'versions': [
                {
                    'method': 'git',
                    'options': {
                        'url': 'the://git/url',
                    },
                    'version': '0.0.1',
                },
            ],
        }

        result, errors = MarketListResultSchema().load(plugin_info)

        assert_that(result, has_entries('versions', contains({'version': '0.0.1'})))


class TestInstallationSchema(TestCase):

    def test_git_options_required(self):
        input_ = {'method': 'git'}
        result, errors = PluginInstallSchema().load(input_)
        assert_that(errors, has_key('options'))

    def test_git_options_url_required(self):
        input_ = {'method': 'git',
                  'options': {}}
        result, errors = PluginInstallSchema().load(input_)
        assert_that(errors, has_entries(options=has_key('url')))

    def test_git_options_ref_default(self):
        input_ = {'method': 'git',
                  'options': {'url': 'file://my-git-repo.git'}}
        result, errors = PluginInstallSchema().load(input_)
        assert_that(result, has_entries(options=has_entries(ref='master')))

    def test_market_options_required(self):
        input_ = {'method': 'market'}
        result, errors = PluginInstallSchema().load(input_)
        assert_that(errors, has_key('options'))

    def test_market_options_namespace_name_required(self):
        input_ = {'method': 'market',
                  'options': {}}
        result, errors = PluginInstallSchema().load(input_)
        assert_that(errors, has_entries(options=all_of(has_key('namespace'), has_key('name'))))

    def test_none(self):
        input_ = None
        result, errors = PluginInstallSchema().load(input_)
        assert_that(errors, has_key('method'))


class TestInstallationSchemaV01(TestCase):

    def test_git_installation_without_ref(self):
        url = 'file://my-git-repo.git'
        input_ = dict(
            url=url,
            method='git',
        )

        result, _ = PluginInstallSchemaV01().load(input_)

        expected = {'url': url, 'method': 'git', 'options': {'ref': 'master'}}
        assert_that(result, equal_to(expected))

    def test_git_installation_with_ref(self):
        url = 'file://my-git-repo.git'
        input_ = dict(
            url=url,
            method='git',
            options={'ref': 'v0.0.1'},
        )

        result, _ = PluginInstallSchemaV01().load(input_)

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

        result, _ = PluginInstallSchemaV01().load(input_)

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
        result, errors = PluginInstallSchemaV01().load({'method': 'foobar',
                                                        'url': 'file:///test'})
        assert_that(
            errors,
            has_entries('method', contains(has_entries('constraint', has_entries('choices', ANY)))))
