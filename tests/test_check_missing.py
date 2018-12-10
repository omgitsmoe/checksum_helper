import os
import shutil
import pytest
import time

from utils import TESTS_DIR, read_file, write_file_str
from checksum_helper import ChecksumHelper


def test_check_missing(capsys):
    os.chdir(TESTS_DIR)
    shutil.copy2("test_check_missing_files/missing.sha512", "test_check_missing_files/tt/")

    # ChecksumHelper sets cwd to first param
    checksum_hlpr = ChecksumHelper("test_check_missing_files/tt", hash_filename_filter=())

    # assert that last test didnt leave a compl.sha512 behind
    try:
        os.remove("compl.sha512")
    except FileNotFoundError:
        pass

    checksum_hlpr.check_missing_files()

    missing = ["D    sub4", "D    sub3\\sub1", "D    sub3\\sub2", "F    new 2.txt",
               "F    sub1\\sub2\\new 2.txt", "F    missing.sha512"]
    # get stdout
    missing_found = capsys.readouterr().out
    missing_found = missing_found.strip().splitlines()[2:]

    assert sorted(missing) == sorted(missing_found)

    os.remove("missing.sha512")

    os.chdir(TESTS_DIR)
    shutil.copy2("test_check_missing_files/compl.sha512", "test_check_missing_files/tt/")
    checksum_hlpr = ChecksumHelper("test_check_missing_files/tt", hash_filename_filter=())
    checksum_hlpr.check_missing_files()

    # get stdout
    missing_found = capsys.readouterr().out
    missing_found = missing_found.strip().splitlines()[2:]

    assert ["F    compl.sha512"] == missing_found

    os.remove("compl.sha512")
