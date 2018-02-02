# Copyright 2018 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0+

from hamcrest import assert_that, equal_to
from unittest import TestCase

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
