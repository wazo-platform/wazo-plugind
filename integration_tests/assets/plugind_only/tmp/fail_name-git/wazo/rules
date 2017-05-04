#!/bin/sh
# Copyright 2017 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0+

case "$1" in
    build)
        echo "Building..."
        # During the build files can be created by wazo-plugind
        echo '1' > build_failed
        ;;
    install)
        echo "Installing..."
        # During the install files cannot be created by root
        echo '1' > install_failed && mv install_failed /tmp/install_failed

        # During the install files can be copied by root
        cp build_failed /tmp
        echo '1' > /tmp/install_failed
        ;;
    *)
        echo "$0 called with unknown argument '$1'" >&2
        exit 1
        ;;
esac
