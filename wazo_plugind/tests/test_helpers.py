# Copyright 2017 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0+

from unittest import TestCase
from hamcrest import assert_that, calling, has_properties
from mock import ANY, Mock, patch
from xivo_test_helpers.hamcrest.raises import raises
from ..helpers import Validator
from ..config import _MAX_PLUGIN_FORMAT_VERSION
from .. import exceptions

CURRENT_WAZO_VERSION = '17.10'


class TestValidator(TestCase):

    def setUp(self):
        self.validator = Validator(Mock(), CURRENT_WAZO_VERSION)

    def test_that_missing_fields_raises(self):
        metadata = self.new_metadata()
        metadata.pop('version', None)

        expected_details = {
            'version': {'constraint_id': 'required',
                        'constraint': 'required',
                        'message': ANY}
        }
        assert_that(
            calling(self.validator.validate).with_args(metadata),
            raises(exceptions.PluginValidationException).matching(
                has_properties('error_id', 'validation_error',
                               'message', 'Validation error',
                               'details', expected_details)
            ),
        )

    def test_that_invalid_name_raises(self):
        metadata = self.new_metadata(name='no_underscore_allowed')

        expected_details = {
            'name': {'constraint_id': 'regex',
                     'constraint': ANY,
                     'message': ANY}
        }
        assert_that(
            calling(self.validator.validate).with_args(metadata),
            raises(exceptions.PluginValidationException).matching(
                has_properties('error_id', 'validation_error',
                               'message', 'Validation error',
                               'details', expected_details)
            ),
        )

    def test_that_invalid_namespace_raises(self):
        metadata = self.new_metadata(namespace='no-dash-allowed')

        expected_details = {
            'namespace': {'constraint_id': 'regex',
                          'constraint': ANY,
                          'message': ANY}
        }
        assert_that(
            calling(self.validator.validate).with_args(metadata),
            raises(exceptions.PluginValidationException).matching(
                has_properties('error_id', 'validation_error',
                               'message', 'Validation error',
                               'details', expected_details)
            ),
        )

    def test_plugin_format_version_from_the_future(self):
        metadata = self.new_metadata(plugin_format_version=_MAX_PLUGIN_FORMAT_VERSION + 1)

        expected_details = {
            'plugin_format_version': {'constraint_id': 'range',
                                      'constraint': {'min': 0, 'max': _MAX_PLUGIN_FORMAT_VERSION},
                                      'message': ANY}}
        assert_that(
            calling(self.validator.validate).with_args(metadata),
            raises(exceptions.PluginValidationException).matching(
                has_properties('error_id', 'validation_error',
                               'message', 'Validation error',
                               'details', expected_details)
            ),
        )

    def test_max_wazo_version_too_small(self):
        metadata = self.new_metadata(max_wazo_version='16.16')

        expected_details = {
            'max_wazo_version': {'constraint_id': 'range',
                                 'constraint': {'min': CURRENT_WAZO_VERSION},
                                 'message': ANY}}
        assert_that(
            calling(self.validator.validate).with_args(metadata),
            raises(exceptions.PluginValidationException).matching(
                has_properties('error_id', 'validation_error',
                               'message', 'Validation error',
                               'details', expected_details)
            ),
        )

    def test_min_wazo_version_too_high(self):
        metadata = self.new_metadata(min_wazo_version='17.11')

        expected_details = {
            'min_wazo_version': {'constraint_id': 'range',
                                 'constraint': {'max': CURRENT_WAZO_VERSION},
                                 'message': ANY}}
        assert_that(
            calling(self.validator.validate).with_args(metadata),
            raises(exceptions.PluginValidationException).matching(
                has_properties('error_id', 'validation_error',
                               'message', 'Validation error',
                               'details', expected_details)
            ),
        )

    def test_plugin_already_installed(self):
        metadata = self.new_metadata()

        with patch.object(self.validator._db, 'is_installed', return_value=True):
            assert_that(calling(self.validator.validate).with_args(metadata),
                        raises(exceptions.PluginAlreadyInstalled))

    def new_metadata(self, name='valid-name', namespace='validns', version='0.0.1', **kwargs):
        metadata = dict(kwargs)
        metadata['name'] = name
        metadata['namespace'] = namespace
        metadata['version'] = version
        return metadata
