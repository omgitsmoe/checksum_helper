import os
import pytest

from checksum_helper import checksum_helper as ch

from utils import TESTS_DIR, setup_tmpdir_param

def test_cshd_was_read_default():
    cshd = ch.ChecksumHelperData(None, "foo")
    assert cshd.was_read is False


def test_cshd_was_read(setup_tmpdir_param):
    tmpdir = setup_tmpdir_param
    cshd_path = os.path.join(tmpdir, "foo.cshd")
    cshd = ch.ChecksumHelperData(None, cshd_path)
    cshd.set_entry("foo", ch.HashedFile("foo", None, "sha512", bytes(0xabcdef), True))
    cshd.write()

    assert cshd.was_read is False

    cshd.read()

    assert cshd.was_read is True

    cshd = ch.ChecksumHelperData(None, cshd_path)
    assert cshd.was_read is False
    cshd.read()
    assert cshd.was_read is True
