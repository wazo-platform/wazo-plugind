# Copyright 2018 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0+

from hamcrest import (
    assert_that,
    calling,
    equal_to,
    raises,
)
from unittest import TestCase

from wazo_plugind import exceptions
from .. import version


class TestComparator(TestCase):

    def setUp(self):
        self.comparator = version.Comparator()

    def test_satisfies(self):
        installed_version = '1.5.2-5'

        tests = {
            # Same version
            '1.5.2-5': True,
            '>1.5.2-5': False,
            '> 1.5.2-5': False,
            '>=1.5.2-5': True,
            '>= 1.5.2-5': True,
            '<1.5.2-5': False,
            '< 1.5.2-5': False,
            '<=1.5.2-5': True,
            '<= 1.5.2-5': True,
            '==1.5.2-5': True,
            '== 1.5.2-5': True,
            '=1.5.2-5': True,
            '= 1.5.2-5': True,

            # Smaller version
            '1.5.1': False,
            '>1.5.1': True,
            '> 1.5.1': True,
            '>=1.5.1': True,
            '>= 1.5.1': True,
            '<1.5.1': False,
            '< 1.5.1': False,
            '<=1.5.1': False,
            '<= 1.5.1': False,
            '==1.5.1': False,
            '== 1.5.1': False,
            '=1.5.1': False,
            '= 1.5.1': False,

            # Bigger version
            '1.5.2-42': False,
            '>1.5.2-42': False,
            '> 1.5.2-42': False,
            '>=1.5.2-42': False,
            '>= 1.5.2-42': False,
            '<1.5.2-42': True,
            '< 1.5.2-42': True,
            '<=1.5.2-42': True,
            '<= 1.5.2-42': True,
            '==1.5.2-42': False,
            '== 1.5.2-42': False,
            '=1.5.2-42': False,
            '= 1.5.2-42': False,

            # multiple
            '>= 1, < 1.5': False,
            '= 1, < 1.5': False,
            '>= 1, < 1.6': True,
            '< 1, > 1.6': False,
            '>= 1, < 1.6, ==42': False,
            '>= 1, < 1.6, ==1.5.2-5': True,
        }

        for required_version, expected in tests.items():
            result = self.comparator.satisfies(installed_version, required_version)
            assert_that(result, equal_to(expected), required_version)

        invalid_version = '>>> 1.5.2'
        assert_that(
            calling(self.comparator.satisfies).with_args(installed_version, invalid_version),
            raises(exceptions.InvalidVersionException),
        )

        invalid_version = '<> 1.5.2'
        assert_that(
            calling(self.comparator.satisfies).with_args(installed_version, invalid_version),
            raises(exceptions.InvalidVersionException),
        )

        invalid_version = '!~ 1.5.2'
        assert_that(
            calling(self.comparator.satisfies).with_args(installed_version, invalid_version),
            raises(exceptions.InvalidVersionException),
        )

        invalid_version = None
        assert_that(
            calling(self.comparator.satisfies).with_args(installed_version, invalid_version),
            raises(exceptions.InvalidVersionException),
        )

    def test_less_than(self):
        assert_that(self.comparator.less_than('17.10', '17.10'), equal_to(False))
        assert_that(self.comparator.less_than('17.09', '17.10'), equal_to(True))
        assert_that(self.comparator.less_than(None, '17.10'), equal_to(True))
        assert_that(self.comparator.less_than('17.10', None), equal_to(False))
        assert_that(self.comparator.less_than('', None), equal_to(True))
        assert_that(self.comparator.less_than('1.0.0', '1.0.0-1'), equal_to(True))
        assert_that(self.comparator.less_than('1.0.1', '1.0.0-1'), equal_to(False))
        assert_that(self.comparator.less_than('1.0.0-2', '1.0.0-10'), equal_to(True))
