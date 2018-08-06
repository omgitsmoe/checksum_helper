import os
import shutil
import pytest
import time

from utils import TESTS_DIR, setup_tmpdir_param, read_file, write_file_str
from checksum_helper import ChecksumHelper


def test_build_most_current(capsys):
    os.chdir(TESTS_DIR)
    shutil.copy2("test_check_missing_files/missing.sha512", "test_check_missing_files/tt/")
    checksum_hlpr = ChecksumHelper("test_check_missing_files/tt", hash_filename_filter=())
    checksum_hlpr.check_missing_files()

    missing = ["new 2.txt", "sub1\sub2\\new 2.txt", "missing.sha512"]
    # get stdout
    missing_found = capsys.readouterr().out
    missing_found = missing_found.strip().replace("Files without checksum (of all files in subdirs, not checked ifchecksums still match the files!):\n", "").split("\n")

    assert sorted(missing) == sorted(missing_found)
    
    os.remove("missing.sha512")

    os.chdir(TESTS_DIR)
    shutil.copy2("test_check_missing_files/compl.sha512", "test_check_missing_files/tt/")
    checksum_hlpr = ChecksumHelper("test_check_missing_files/tt", hash_filename_filter=())
    checksum_hlpr.check_missing_files()

    # get stdout
    missing_found = capsys.readouterr().out
    missing_found = missing_found.strip().replace("Files without checksum (of all files in subdirs, not checked ifchecksums still match the files!):\n", "").split("\n")

    assert ["compl.sha512"] == missing_found
    
    os.remove("compl.sha512")
    

