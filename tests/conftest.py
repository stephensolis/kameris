from backports.tempfile import TemporaryDirectory
import pytest


@pytest.fixture(scope='session')
def shared_tempdir():
    d = TemporaryDirectory()
    yield d.name
    try:
        d.cleanup()
    except Exception:
        pass
