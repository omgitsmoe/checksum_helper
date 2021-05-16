import os
import pytest

from utils import TESTS_DIR

@pytest.fixture(scope="session", autouse=True)
def set_mtimes():
    # since some tests (mostly verify, most_current and incremental) require
    # the test files to have to correct modification times to work (which is the
    # newest hash file, log under Warning level if the file changed but
    # the mtime did not etc.) we set them here once per session
    with open(os.path.join(TESTS_DIR, "tests_mtimes.txt"), 'r') as f:
        lines = f.readlines()

    for ln in lines:
        mtime_str, relpath = ln.strip().split(" ", 1)
        mtime = float(mtime_str)
        os.utime(os.path.join(TESTS_DIR, relpath), times=(mtime, mtime))
