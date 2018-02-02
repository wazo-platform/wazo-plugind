# Copyright 2017-2018 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0+

from unittest import TestCase
from hamcrest import assert_that, contains, has_entries, all_of, has_key

from ..schema import MarketListResultSchema, PluginInstallSchema


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
