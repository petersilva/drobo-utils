#!/bin/sh 
## Taken from ipython package, kudos to maintainer :)

set -e

#command --upstream-version version filename

[ $# -eq 3 ] || exit 255

echo

version="$2"
filename="$3"
dfsgfilename=`echo $3 | sed 's,\.orig\.,+repack.orig.,'`

tar xfz ${filename} 

dir=`tar tfz ${filename} | head -1 | sed 's,/.*,,g'`
rm -f ${filename}

rm -rf ${dir}/debian ${dir}/notdebian
mv ${dir} ${dir}+repack.orig

tar cf - ${dir}+repack.orig | gzip -9 > ${dfsgfilename}

rm -rf ${dir}+repack.orig

echo "${dfsgfilename} created."
