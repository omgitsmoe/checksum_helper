import os
import shutil

from utils import TESTS_DIR
from checksum_helper.checksum_helper import ChecksumHelper


def test_check_missing(capsys):
    root_dir = os.path.join(TESTS_DIR, "test_check_missing_files")
    # empty string at the end so 2nd param ends up as path/ or path\\ -> dir
    shutil.copy2(os.path.join(root_dir, "missing.sha512"),
                 os.path.join(root_dir, "tt", ""))

    checksum_hlpr = ChecksumHelper(os.path.join(
        root_dir, "tt"), hash_filename_filter=())

    # assert that last test didnt leave a compl.sha512 behind
    try:
        os.remove(os.path.join(root_dir, "tt", "compl.sha512"))
    except FileNotFoundError:
        pass

    checksum_hlpr.check_missing_files()

    missing = ["D    sub4", f"D    sub3{os.sep}sub1", f"D    sub3{os.sep}sub2", "F    new 2.txt",
               f"F    sub1{os.sep}sub2{os.sep}new 2.txt", "F    missing.sha512"]
    # CAREFUL using print here for print-debugging will lead to the ouput being captured
    # by capsys.readouterr() and thus messing with the test
    # get stdout
    missing_found = capsys.readouterr().out
    missing_found = missing_found.strip().splitlines()[2:]

    assert sorted(missing) == sorted(missing_found)

    os.remove(os.path.join(root_dir, "tt", "missing.sha512"))

    shutil.copy2(os.path.join(root_dir, "compl.sha512"),
                 os.path.join(root_dir, "tt", ""))
    checksum_hlpr = ChecksumHelper(os.path.join(
        root_dir, "tt"), hash_filename_filter=())
    checksum_hlpr.check_missing_files()

    # get stdout
    missing_found = capsys.readouterr().out
    missing_found = missing_found.strip().splitlines()[2:]

    assert ["F    compl.sha512"] == missing_found

    os.remove(os.path.join(root_dir, "tt", "compl.sha512"))
