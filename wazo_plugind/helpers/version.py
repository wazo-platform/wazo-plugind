# Copyright 2018 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0+

import logging
import re

from distutils.version import LooseVersion

from wazo_plugind import exceptions

logger = logging.getLogger(__name__)
VERSION_RE = re.compile(r'^\s?([=<>]*)\s?([0-9\-.a-b~]+)\s?$')


class Comparator:

    def satisfies(self, version, required_version):
        version = _make_comparable_version(version)
        try:
            required_version = required_version.replace(' ', '')
        except AttributeError:
            raise exceptions.InvalidVersionException(required_version)

        return self._cmp_version_string(version, required_version)

    @staticmethod
    def less_than(left, right):
        if not left:
            return True
        if not right:
            return False

        left = _make_comparable_version(left)
        right = _make_comparable_version(right)

        return left < right

    def _cmp_version_string(self, version, required_version):
        if not required_version:
            return True

        for operator, extracted_version in _operator_version(required_version):
            if not self._cmp_versions(operator, version, extracted_version):
                return False

        return True

    @staticmethod
    def _cmp_versions(operator, left, right):
        if operator == '>':
            return left > right
        if operator == '>=':
            return left >= right
        elif operator == '<':
            return left < right
        elif operator == '<=':
            return left <= right
        else:
            return left == right


class Debianizer:

    _operator_map = {
        '': '=',
        '=': '=',
        '==': '=',
        '>=': '>=',
        '>': '>>',
        '<': '<<',
        '<=': '<=',
    }
    _debian_package_name_fmt = 'wazo-plugind-{name}-{namespace}'
    _debian_package_name_version_fmt = 'wazo-plugind-{name}-{namespace} ({operator} {version})'

    def debianize(self, dependency):
        version_string = dependency.get('version', '')
        if version_string:
            for operator, version in _operator_version(version_string):
                yield self._debian_package_name_version_fmt.format(
                    operator=self._operator_map[operator],
                    version=version,
                    name=dependency['name'],
                    namespace=dependency['namespace'],
                )
        else:
            yield self._debian_package_name_fmt.format(**dependency)


def _operator_version(version_string):
    versions = version_string.split(',')
    for s in versions:
        result = VERSION_RE.match(s)
        if not result:
            logger.info('parsing an invalid version: %s', version_string)
            raise exceptions.InvalidVersionException(version_string)
        operator, version = result.groups()
        yield operator, _make_comparable_version(version)


def _make_comparable_version(version):
    try:
        value_tmp = LooseVersion(version)
        value_tmp.version  # raise AttributeError if value is None
        version = value_tmp
    except (TypeError, AttributeError):
        # Integer raise TypeError
        # Not a valid version number fallback to alphabetic ordering
        version = str(version)

    return version
