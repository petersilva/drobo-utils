
clean:
	-rm CHANGES.html DEVELOPERS.html README.html
	-rm -rf build*

doc:
	rst2html README.txt >README.html
	rst2html DEVELOPERS.txt >DEVELOPERS.html
	rst2html CHANGES.txt >CHANGES.html
