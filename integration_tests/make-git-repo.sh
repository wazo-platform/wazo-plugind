#!/bin/bash
# Copyright 2017-2018 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

set -eu

for dir in $(find . -name '*-git'); do
    new_name="${dir::-4}"
    rm -rf "$new_name"
    cp -R "$dir" "$new_name"
    pushd "$new_name"
    git init
    git add -A
    git commit --no-gpg-sign -m 'initial commit'
    popd
done

pushd "assets/git/git-plugind_only/repo"
git checkout -b "v2"
sed -i 's/package_success/package_success_2/' wazo/rules
sed -i 's/0.0.1/0.0.2/' wazo/plugin.yml
sed -i '/debian_depends/,/tig/d' wazo/plugin.yml
git add -u
git commit --no-gpg-sign -m 'second commit'
popd
