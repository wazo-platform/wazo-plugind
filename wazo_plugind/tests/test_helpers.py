# Copyright 2017 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0+

from unittest import TestCase
from hamcrest import assert_that, calling, raises
from mock import patch
from ..helpers import Validator
from ..config import _DEFAULT_CONFIG, _MAX_PLUGIN_FORMAT_VERSION
from .. import exceptions


class TestValidator(TestCase):

    def setUp(self):
        self.validator = Validator(_DEFAULT_CONFIG)

    def test_that_missing_fields_raises(self):
        metadata = self.new_metadata()
        metadata.pop('version', None)

        assert_that(calling(self.validator.validate).with_args(metadata),
                    raises(exceptions.MissingFieldException))

    def test_that_invalid_name_raises(self):
        metadata = self.new_metadata(name='no_underscore_allowed')

        assert_that(calling(self.validator.validate).with_args(metadata),
                    raises(exceptions.InvalidNameException))

    def test_that_invalid_namespace_raises(self):
        metadata = self.new_metadata(namespace='no-dash-allowed')

        assert_that(calling(self.validator.validate).with_args(metadata),
                    raises(exceptions.InvalidNamespaceException))

    def test_plugin_format_version_from_the_future(self):
        metadata = self.new_metadata(plugin_format_version=_MAX_PLUGIN_FORMAT_VERSION + 1)

        assert_that(calling(self.validator.validate).with_args(metadata),
                    raises(exceptions.InvalidPluginFormatVersion))

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
