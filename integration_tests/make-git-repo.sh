#!/bin/bash

for dir in $(find . -name '*-git'); do
    new_name=$(echo $dir | awk -F'-' '{ print $1 }')
    cp -R $dir $new_name
    pushd $new_name
    git init
    git add -A
    git commit --no-gpg-sign -m 'initial commit'
    popd
done
