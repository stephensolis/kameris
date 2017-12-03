.PHONY: all pip-package bin-package distribute clean lint

# this allows the makefile to be both GNU make and nmake compatible
# \
!ifndef 0 # \
# nmake stuff \
CLEAN_CMD = rd /s /q build dist modmap_toolkit.egg-info || del /s *.pyc *.pyo || VER>NUL # \
!else
# make stuff
CLEAN_CMD = rm -rf build dist modmap_toolkit.egg-info && find . -type f \( -name '*.pyc' -o -name '*.pyo' \) -delete
# \
!endif

all: pip-package bin-package


pip-package: clean
	python setup.py sdist
	pip install --upgrade wheel
	python setup.py bdist_wheel --universal

bin-package:
	pip install --upgrade pyinstaller
	python -m PyInstaller modmap-toolkit.spec

distribute: pip-package
	pip install --upgrade twine
	python -m twine upload dist/*.whl dist/*.tar.*


clean:
	$(CLEAN_CMD)


lint:
	python -m flake8 modmap_toolkit modmap-toolkit.py setup.py
