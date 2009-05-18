#!/usr/bin/make -f

build: doc
	python setup.py build

clean:
	-python setup.py clean
	-find . -name "*\.pyc" -delete
	-rm CHANGES.html DEVELOPERS.html README.html
	-rm -rf build*

doc:
	rst2html README.txt >README.html
	rst2html DEVELOPERS.txt >DEVELOPERS.html
	rst2html CHANGES.txt >CHANGES.html

# Uncomment this to turn on verbose mode.

PKGNAME := drobo-utils

install: build
	python setup.py install_lib -d /usr/lib/python/site-packages; 
	python setup.py install_data -d /usr/share/$(PKGNAME)
	python setup.py install_scripts -d /usr/sbin

release:
	./make_tarball.sh
	debuild -i
