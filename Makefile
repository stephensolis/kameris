.PHONY: all pip-package bin-package distribute distribute-pip distribute-bin test pytest lint install uninstall clean

VERSION_NUMBER = $(shell python -c 'import kameris; print(kameris.__version__)')
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
	python -m pip install --upgrade setuptools wheel
	python setup.py bdist_wheel --universal

bin-package:
	python -m pip install --upgrade pyinstaller
	python -m PyInstaller kameris.spec

distribute: distribute-pip distribute-bin

distribute-pip: pip-package
	python -m pip install --upgrade twine
	python -m twine upload dist/*.whl

distribute-bin: bin-package
	-external/github-release/github-release$(EXE_SUFFIX) release --user stephensolis --repo kameris \
																 --tag v$(VERSION_NUMBER) --name v$(VERSION_NUMBER)
	external/github-release/github-release$(EXE_SUFFIX) upload --user stephensolis --repo kameris \
															   --tag v$(VERSION_NUMBER) \
															   --name kameris$(EXE_SUFFIX) \
															   --file dist/kameris$(EXE_SUFFIX)


test: pytest lint

pytest:
	python -m pytest -s -v --cov=./
ifdef SEND_COVERAGE
	pip install codecov python-coveralls
	python -m codecov
	python -c "import coveralls; coveralls.wear()"
endif

lint:
	python -m flake8 .


install:
	python -m pip install -e .

uninstall:
	python -m pip uninstall kameris


clean:
	bash -c 'rm -rf build dist kameris.egg-info && find . -type f \( -name '*.pyc' -o -name '*.pyo' \) -delete'
