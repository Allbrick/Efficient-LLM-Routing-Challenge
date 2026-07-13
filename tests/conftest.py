import os
import shutil

import pytest


@pytest.fixture
def tmp_dir():
    """Windows tmp_path 권한 문제를 우회하는 임시 디렉토리."""
    d = os.path.join(os.path.dirname(__file__), ".tmp_test")
    os.makedirs(d, exist_ok=True)
    yield d
    shutil.rmtree(d, ignore_errors=True)
