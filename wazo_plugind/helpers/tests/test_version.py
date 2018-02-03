# Copyright 2018 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0+

from hamcrest import (
    assert_that,
    calling,
    equal_to,
    contains,
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


class TestDebianizer(TestCase):

    def setUp(self):
        self.debianizer = version.Debianizer()

    def test_debianize(self):
        name, namespace = 'foo', 'bar'
        debian_package = 'wazo-plugind-foo-bar'
        version = '1.5.5'
        plugin_info = dict(name=name, namespace=namespace)

        assert_that(
            self.debianizer.debianize(plugin_info),
            contains(debian_package),
        )

        tests = [
            ('1.5.5', '='),
            ('=1.5.5', '='),
            ('==1.5.5', '='),
            ('= 1.5.5', '='),
            ('== 1.5.5', '='),
            ('>=1.5.5', '>='),
            ('>= 1.5.5', '>='),
            ('> 1.5.5', '>>'),
            ('>1.5.5', '>>'),
            ('<1.5.5', '<<'),
            ('< 1.5.5', '<<'),
            ('<= 1.5.5', '<='),
            ('<=1.5.5', '<='),
        ]

        for plugin_version, operator in tests:
            plugin_info['version'] = plugin_version
            expected = '{} ({} {})'.format(debian_package, operator, version)
            assert_that(
                self.debianizer.debianize(plugin_info),
                contains(expected),
                plugin_version,
            )

        plugin_info['version'] = '>= 1.5.5, < 2'
        assert_that(
            self.debianizer.debianize(plugin_info),
            contains(
                '{} ({} {})'.format(debian_package, '>=', '1.5.5'),
                '{} ({} {})'.format(debian_package, '<<', '2'),
            )
        )

        # calling(list) is used to consume the generator and actually raise the exception
        plugin_info['version'] = '~= 1.5.12'
        assert_that(
            calling(list).with_args(self.debianizer.debianize(plugin_info)),
            raises(exceptions.InvalidVersionException),
        )
