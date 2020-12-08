#!/usr/bin/make -f

build: doc
	python setup.py build

clean:
	-python setup.py clean
	-find . -name "*\.pyc" -delete
	-rm *.html
	-rm -rf build*

doc:
	groff -Thtml -man drobom.8 >drobom.html
	groff -Thtml -man droboview.8 >droboview.html
	rst2html --stylesheet-path=drobo-utils.css README.rst >README.html
	rst2html --stylesheet-path=drobo-utils.css DEVELOPERS.rst >DEVELOPERS.html
	rst2html --stylesheet-path=drobo-utils.css CHANGES.rst >CHANGES.html
	rst2html --stylesheet-path=drobo-utils.css DroboShare.rst >DroboShare.html
	rst2html --stylesheet-path=drobo-utils.css index.rst >index.html

# Uncomment this to turn on verbose mode.

PKGNAME := drobo-utils

install: build
	python setup.py install_lib -d /usr/lib/python/site-packages; 
	python setup.py install_data -d /usr/share/$(PKGNAME)
	python setup.py install_scripts -d /usr/sbin

release:
	./make_tarball.sh
	debuild -i
