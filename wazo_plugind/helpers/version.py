# Copyright 2018 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0+

from distutils.version import LooseVersion


class Comparator:

    @staticmethod
    def less_than(left, right):
        if not left:
            return True
        if not right:
            return False

        left = _make_comparable_version(left)
        right = _make_comparable_version(right)

        return left < right


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
