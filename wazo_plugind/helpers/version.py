# Copyright 2018 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0+

from distutils.version import LooseVersion


class Comparator:

    def satisfies(self, version, required_version):
        version = _make_comparable_version(version)
        required_version = required_version.replace(' ', '')

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

        operator, end = _extract_operator(required_version)
        extracted_version, end = _extract_version(end)

        current = self._cmp_versions(operator, version, extracted_version)
        return current and self._cmp_version_string(version, end)

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
        version_string = dependency.get('version', '').replace(' ', '')
        if not version_string:
            yield self._debian_package_name_fmt.format(**dependency)

        end = version_string
        while end:
            operator, end = _extract_operator(end)
            version, end = _extract_version(end)

            # TODO what to do if the operator is invalid? ex <> or !> KeyError at the moment
            yield self._debian_package_name_version_fmt.format(
                operator=self._operator_map[operator],
                version=version,
                name=dependency['name'],
                namespace=dependency['namespace'],
            )


def _extract_operator(s):
    operator_chars = ['=', '>', '<']
    for i, c in enumerate(s):
        if c in operator_chars:
            continue
        operator = s[:i]
        end = s[i:]
        return operator, end


def _extract_version(s):
    if ',' not in s:
        return s, None

    version, end = s.split(',', 1)
    return _make_comparable_version(version), end or None


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
