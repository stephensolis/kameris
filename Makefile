.PHONY: all pip-package bin-package distribute distribute-pip distribute-bin lint install uninstall clean

CLEAN_CMD = bash -c 'rm -rf build dist modmap_toolkit.egg-info && find . -type f \( -name '*.pyc' -o -name '*.pyo' \) -delete'
VERSION_NUMBER = $(shell python -c 'import modmap_toolkit; print(modmap_toolkit.__version__)')
ifeq ($(OS),Windows_NT)
	EXE_SUFFIX = -windows.exe
else
	PLATFORM = $(shell uname -s)
	ifeq ($(PLATFORM),Linux)
		EXE_SUFFIX = -linux
	endif
	ifeq ($(PLATFORM),Darwin)
		EXE_SUFFIX = -mac
	endif
endif


all: pip-package bin-package

pip-package: clean
	python -m pip install --upgrade setuptools
	python setup.py sdist
	python -m pip install --upgrade wheel
	python setup.py bdist_wheel --universal

bin-package:
	python -m pip install --upgrade pyinstaller
	python -m PyInstaller modmap-toolkit.spec

distribute: distribute-pip distribute-bin

distribute-pip: pip-package
	python -m pip install --upgrade twine
	python -m twine upload dist/*.whl dist/*.tar.*

distribute-bin: bin-package
	tools/github-release/github-release$(EXE_SUFFIX) upload --user stephensolis --repo modmap-toolkit \
															--tag v$(VERSION_NUMBER) \
															--name modmap-toolkit$(EXE_SUFFIX) \
															--file dist/modmap-toolkit$(EXE_SUFFIX)


lint:
	python -m flake8 modmap_toolkit modmap-toolkit.py setup.py


install:
	python -m pip install -e .

uninstall:
	python -m pip uninstall modmap-toolkit


clean:
	$(CLEAN_CMD)
