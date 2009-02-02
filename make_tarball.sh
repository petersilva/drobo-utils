#!/bin/bash
version=$(python setup.py --version)
mkdir ../drobo-utils-$version
cp -a * ../drobo-utils-$version
cd ..
tar zcf drobo-utils_$version.orig.tar.gz --exclude debian --exclude .svn --exclude *.pyc --exclude build* drobo-utils-$version
rm -rf drobo-utils-$version
