# Copyright 2017-2025 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

from unittest import TestCase

from hamcrest import (
    all_of,
    assert_that,
    calling,
    contains_exactly,
    has_entries,
    has_entry,
    has_key,
    has_property,
)
from marshmallow import ValidationError
from wazo_test_helpers.hamcrest.raises import raises

from ..schema import MarketListResultSchema, PluginInstallSchema


class TestMarketResultSchema(TestCase):
    def test_that_install_options_are_removed(self):
        plugin_info = {
            'name': 'foo',
            'namespace': 'foobar',
            'versions': [
                {
                    'method': 'git',
                    'options': {'url': 'the://git/url'},
                    'version': '0.0.1',
                    'upgradable': True,
                },
            ],
        }

        result = MarketListResultSchema().load(plugin_info)

        assert_that(
            result,
            has_entries(
                'versions', contains_exactly({'version': '0.0.1', 'upgradable': True})
            ),
        )


class TestInstallationSchema(TestCase):
    def test_git_options_required(self):
        input_ = {'method': 'git'}
        assert_that(
            calling(PluginInstallSchema().load).with_args(input_),
            raises(ValidationError, has_property('messages', has_key('options'))),
        )

    def test_git_options_url_required(self):
        input_ = {'method': 'git', 'options': {}}
        assert_that(
            calling(PluginInstallSchema().load).with_args(input_),
            raises(
                ValidationError,
                has_property('messages', has_entry('options', has_key('url'))),
            ),
        )

    def test_git_options_default_values(self):
        input_ = {'method': 'git', 'options': {'url': 'file://my-git-repo.git'}}
        result = PluginInstallSchema().load(input_)
        assert_that(
            result,
            has_entries(
                options=has_entries(
                    ref='master',
                    subdirectory=None,
                )
            ),
        )

    def test_market_options_required(self):
        input_ = {'method': 'market'}
        assert_that(
            calling(PluginInstallSchema().load).with_args(input_),
            raises(ValidationError, has_property('messages', has_key('options'))),
        )

    def test_market_options_namespace_name_required(self):
        input_ = {'method': 'market', 'options': {}}
        assert_that(
            calling(PluginInstallSchema().load).with_args(input_),
            raises(
                ValidationError,
                has_property(
                    'messages',
                    has_entries(options=all_of(has_key('namespace'), has_key('name'))),
                ),
            ),
        )

    def test_none(self):
        input_ = None
        assert_that(
            calling(PluginInstallSchema().load).with_args(input_),
            raises(ValidationError, has_property('messages', has_key('method'))),
        )
