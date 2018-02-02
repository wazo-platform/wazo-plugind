# Copyright 2018 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0+

from distutils.version import LooseVersion


class Comparator:

    def satisfies(self, version, required_version):
        version = LooseVersion(version)
        required_version = required_version.replace(' ', '')

        return self._cmp_version_string(version, required_version)

    def _cmp_version_string(self, version, required_version):
        if not required_version:
            return True

        operator, end = self._extract_operator(required_version)
        extracted_version, end = self._extract_version(end)

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

    @staticmethod
    def _extract_version(s):
        if ',' not in s:
            return s, None

        version, end = s.split(',', 1)
        return LooseVersion(version), end or None

    @staticmethod
    def _extract_operator(s):
        operator_chars = ['=', '>', '<']
        for i, c in enumerate(s):
            if c in operator_chars:
                continue
            operator = s[:i]
            end = s[i:]
            return operator, end
