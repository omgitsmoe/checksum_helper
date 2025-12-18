import os
import logging

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


def test_cshd_handles_empty_lines(setup_tmpdir_param):
    tmpdir = setup_tmpdir_param
    cshd_path = os.path.join(tmpdir, "foo.cshd")

    with open(cshd_path, 'w', encoding='utf-8') as f:
        f.write(
"""

1337.1337,md5,deadbeef foo/bar/baz/xer.txt

1337.1337,md5,abcdef goo.mp4

""")

    cshd = ch.ChecksumHelperData(None, cshd_path)
    assert cshd.was_read is False
    cshd.read()
    assert cshd.was_read is True
    assert len(cshd) == 2
    assert cshd.get_entry(os.path.join(tmpdir, 'foo/bar/baz/xer.txt'))
    assert cshd.get_entry(os.path.join(tmpdir, 'goo.mp4'))


def test_cshd_single_hash_handles_empty_lines(setup_tmpdir_param):
    tmpdir = setup_tmpdir_param
    cshd_path = os.path.join(tmpdir, "foo.md5")

    with open(cshd_path, 'w', encoding='utf-8') as f:
        f.write(
"""

deadbeef  foo/bar/baz/xer.txt

abcdef  goo.mp4

""")

    cshd = ch.ChecksumHelperData(None, cshd_path)
    assert cshd.was_read is False
    cshd.read()
    assert cshd.was_read is True
    assert len(cshd) == 2
    assert cshd.get_entry(os.path.join(tmpdir, 'foo/bar/baz/xer.txt'))
    assert cshd.get_entry(os.path.join(tmpdir, 'goo.mp4'))


def test_cshd_not_read_on_invalid_hash_line(setup_tmpdir_param):
    tmpdir = setup_tmpdir_param
    cshd_path = os.path.join(tmpdir, "foo.cshd")

    with open(cshd_path, 'w', encoding='utf-8') as f:
        f.write(
"""

askdfjks fksdsk 24342

""")

    cshd = ch.ChecksumHelperData(None, cshd_path)
    assert cshd.was_read is False
    cshd.read()
    assert cshd.was_read is False
    assert len(cshd) == 0


def test_cshd_logs_faulty_hash_line(setup_tmpdir_param, caplog):
    tmpdir = setup_tmpdir_param
    cshd_path = os.path.join(tmpdir, "foo.cshd")

    faulty_line = 'abcef  sdkfjks'
    with open(cshd_path, 'w', encoding='utf-8') as f:
        f.write(
f"""


{faulty_line}

""")

    caplog.set_level(logging.INFO, logger='checksum_helper.checksum_helper')

    cshd = ch.ChecksumHelperData(None, cshd_path)
    assert cshd.was_read is False
    cshd.read()

    assert (
        'checksum_helper.checksum_helper', logging.WARN, f"File will be skipped: Malformed hash file: Invalid hash line at line 4 in file '{cshd_path}': '{faulty_line}'"
    ) in caplog.record_tuples


def test_cshd_single_hash_logs_faulty_hash_line(setup_tmpdir_param, caplog):
    tmpdir = setup_tmpdir_param
    cshd_path = os.path.join(tmpdir, "foo.md5")

    faulty_line = 'sdkfjks'
    with open(cshd_path, 'w', encoding='utf-8') as f:
        f.write(
f"""


{faulty_line}

""")

    caplog.set_level(logging.INFO, logger='checksum_helper.checksum_helper')

    cshd = ch.ChecksumHelperData(None, cshd_path)
    assert cshd.was_read is False
    cshd.read()

    assert (
        'checksum_helper.checksum_helper', logging.WARN, f"File will be skipped: Malformed hash file: Expected a line like '[0-9a-fA-F]+ ( |*)[^/]+', got '{faulty_line}' on line 4 in file '{cshd_path}'."
    ) in caplog.record_tuples


def test_cshd_warns_pardir_ref(setup_tmpdir_param, caplog):
    tmpdir = setup_tmpdir_param
    cshd_path = os.path.join(tmpdir, "foo.cshd")

    pardir_line = f"1337.1337,md5,deadbeef ..{os.sep}foo{os.sep}bar{os.sep}baz{os.sep}xer.txt"
    print(pardir_line)
    with open(cshd_path, 'w', encoding='utf-8') as f:
        f.write(pardir_line)

    caplog.set_level(logging.INFO, logger='checksum_helper.checksum_helper')

    cshd = ch.ChecksumHelperData(None, cshd_path)
    assert cshd.was_read is False
    cshd.read()
    assert cshd.was_read is True
    assert len(cshd) == 1
    assert cshd.get_entry(os.path.join(tmpdir, '../foo/bar/baz/xer.txt')) is not None

    assert (
        'checksum_helper.checksum_helper', logging.WARN,
        "Found reference beyond the hash file's root dir "
        f"on line 1 in file: '{cshd_path}': '{pardir_line}'. "
        "Consider moving/copying the file using "
        "ChecksumHelper move/copy "
        "to the path that is the most common denominator!",
    ) in caplog.record_tuples


def test_cshd_single_hash_warns_pardir_ref(setup_tmpdir_param, caplog):
    tmpdir = setup_tmpdir_param
    cshd_path = os.path.join(tmpdir, "foo.md5")

    pardir_line = f"deadbeef  ..{os.sep}foo{os.sep}bar{os.sep}baz{os.sep}xer.txt"
    with open(cshd_path, 'w', encoding='utf-8') as f:
        f.write(pardir_line)

    caplog.set_level(logging.INFO, logger='checksum_helper.checksum_helper')

    cshd = ch.ChecksumHelperData(None, cshd_path)
    assert cshd.was_read is False
    cshd.read()
    assert cshd.was_read is True
    assert len(cshd) == 1
    assert cshd.get_entry(os.path.join(tmpdir, '../foo/bar/baz/xer.txt')) is not None

    assert (
        'checksum_helper.checksum_helper', logging.WARN,
        "Found reference beyond the hash file's root dir "
        f"on line 1 in file: '{cshd_path}': '{pardir_line}'. "
        "Consider moving/copying the file using "
        "ChecksumHelper move/copy "
        "to the path that is the most common denominator!",
    ) in caplog.record_tuples



def test_cshd_no_warn_pardir_when_pardir_in_path(setup_tmpdir_param, caplog):
    tmpdir = setup_tmpdir_param
    cshd_path = os.path.join(tmpdir, "foo.cshd")

    with open(cshd_path, 'w', encoding='utf-8') as f:
        f.write(r"""
1337.1337,md5,deadbeef foo/../bar/baz/xer.txt
1337.1337,md5,deadbeef foo/bar/baz../xer.txt
1337.1337,md5,deadbeef foo\..\bar\baz\xer.txt
1337.1337,md5,deadbeef foo\bar\baz..\xer.txt
        """)

    caplog.set_level(logging.INFO, logger='checksum_helper.checksum_helper')

    cshd = ch.ChecksumHelperData(None, cshd_path)
    assert cshd.was_read is False
    cshd.read()
    assert cshd.was_read is True
    assert len(cshd) > 0


    logged_warnings = any(
        1 for _, log_level, _ in caplog.record_tuples if log_level == logging.WARN)
    assert not logged_warnings


def test_cshd_single_hash_no_warn_pardir_when_pardir_in_path(setup_tmpdir_param, caplog):
    tmpdir = setup_tmpdir_param
    cshd_path = os.path.join(tmpdir, "foo.md5")

    with open(cshd_path, 'w', encoding='utf-8') as f:
        f.write(r"""
deadbeef  foo/../bar/baz/xer.txt
deadbeef  foo/bar/baz../xer.txt
deadbeef  foo\..\bar\baz\xer.txt
deadbeef  foo\bar\baz..\xer.txt
        """)

    caplog.set_level(logging.INFO, logger='checksum_helper.checksum_helper')

    cshd = ch.ChecksumHelperData(None, cshd_path)
    assert cshd.was_read is False
    cshd.read()
    assert cshd.was_read is True
    assert len(cshd) > 0


    logged_warnings = any(
        1 for _, log_level, _ in caplog.record_tuples if log_level == logging.WARN)
    assert not logged_warnings

