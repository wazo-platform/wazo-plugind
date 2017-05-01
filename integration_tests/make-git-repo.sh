#!/bin/bash
# Copyright 2017 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0+

set -eu

for dir in $(find . -name '*-git'); do
    new_name=$(echo "$dir" | awk -F'-' '{ print $1 }')
    rm -rf "$new_name"
    cp -R "$dir" "$new_name"
    pushd "$new_name"
    git init
    git add -A
    git commit --no-gpg-sign -m 'initial commit'
    popd
done
