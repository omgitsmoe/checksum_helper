import os
import logging
import time
import pytest

from utils import TESTS_DIR, Args, hash_contents

from checksum_helper import ChecksumHelper, _cl_verify_hfile, _cl_verify_all, _cl_verify_filter


def x_contains_all_y(x, y) -> None:
    for yy in y:
        assert yy in x


@pytest.fixture
def verify_cshd_2failed_files():
    test_verify_root = os.path.join(TESTS_DIR, "test_verify_files", "tt")
    hfile_path = os.path.join(
        test_verify_root, "new_cshd_1+3+missing_edit.cshd")
    hfile_path_old = os.path.join(
        test_verify_root, "new_cshd_1+3+missing.cshd")
    with open(hfile_path_old, "r", encoding="UTF-8-SIG") as f:
        hf_contents = f.read()

    # create 2 files with wrong checksums
    corrupt_file_path = os.path.join(
        test_verify_root, "same_mtime_corrupt.txt")
    with open(corrupt_file_path, "w", encoding="utf-8") as f:
        f.write("same_mtime_corrupt")
    corrupt_file_mtime = os.stat(corrupt_file_path).st_mtime

    older_file_path = os.path.join(test_verify_root, "older_mtime_fail.txt")
    with open(older_file_path, "w", encoding="utf-8") as f:
        f.write("older_mtime_fail")
    older_file_mtime = os.stat(older_file_path).st_mtime

    hf_contents = f"{hf_contents.strip()}\n{corrupt_file_mtime},sha512,ea28ce6b962ad4d481795e93d8ac72104c1eb5c474fdfef54c3693833859fd0bfc047e6ecaa09412c237f2d835d2bfdf1801f8ac2de2edc02fa6d571af9e3405 same_mtime_corrupt.txt\n{older_file_mtime + 2},sha512,ea28ce6b961ad4d481795e93d8ac42104c1eb5c474fdfef54c3693833859fd0bfc047e6ecaa09412c237f2d835d2bfdf1801f8ac2de2edc02fa6d571af9e3405 older_mtime_fail.txt"
    with open(hfile_path, "w", encoding="UTF-8") as w:
        w.write(hf_contents)

    yield hfile_path

    os.remove(corrupt_file_path)
    os.remove(older_file_path)
    os.remove(hfile_path)


def test_verify_cshd(caplog, verify_cshd_2failed_files):
    test_verify_root = os.path.join(TESTS_DIR, "test_verify_files", "tt")
    hfile_path = verify_cshd_2failed_files
    # caplog.set_level sets on root logger by default which is somehow not the logger setup by
    # checksum_helper so specify our logger in the kw param
    caplog.set_level(logging.INFO, logger='Checksum_Helper')
    # ------------ 3 wrong crc, 1 missing ----------
    a = Args(hash_file_name=[hfile_path])
    starting_cwd = os.getcwd()

    caplog.clear()
    # files_total, nr_matches, nr_missing, nr_crc_errors
    assert _cl_verify_hfile(a) == (5, 1, 1, 3)
    # cwd hasn't changed
    assert starting_cwd == os.getcwd()
    x_contains_all_y(caplog.record_tuples, [
        ('Checksum_Helper', logging.INFO, 'new_cshd.txt: SHA512 OK'),
        ('Checksum_Helper', logging.WARNING,
         f'sub1{os.sep}new_cshd_3.txt: SHA512 FAILED -> OUTDATED HASH (file is newer)'),
        ('Checksum_Helper', logging.WARNING,
         f'sub2{os.sep}new_cshd_missing.txt: MISSING'),
        ('Checksum_Helper', logging.ERROR,
         'same_mtime_corrupt.txt: SHA512 FAILED -> CORRUPTED (same modification time)'),
        ('Checksum_Helper', logging.WARNING,
         'older_mtime_fail.txt: SHA512 FAILED -> OUTDATED HASH (file is older)'),
        ('Checksum_Helper', logging.WARNING,
         f'{hfile_path}: 3 files with wrong CRCs!'),
        ('Checksum_Helper', logging.WARNING,
         f'{hfile_path}: 1 missing files!'),
        ('Checksum_Helper', logging.INFO,
         f'Verified hash file(s): {hfile_path}'),
        ('Checksum_Helper', logging.WARNING, f'\nMISSING FILES:\n\n    ROOT FOLDER: {test_verify_root}{os.sep}\n    |--> sub2{os.sep}new_cshd_missing.txt\n\nFAILED CHECKSUMS:\n\n    ROOT FOLDER: {test_verify_root}{os.sep}\n    |--> OUTDATED HASH (file is newer): sub1{os.sep}new_cshd_3.txt\n    |--> CORRUPTED (same modification time): same_mtime_corrupt.txt\n    |--> OUTDATED HASH (file is older): older_mtime_fail.txt\n\nSUMMARY:\n    TOTAL FILES: 5\n    MATCHES: 1\n    FAILED CHECKSUMS: 3\n    MISSING: 1'),
    ])


def test_verify_hfile_warn_beyond_root_and_wrong_crc(caplog):
    test_verify_root = os.path.join(TESTS_DIR, "test_verify_files", "tt")
    # caplog.set_level sets on root logger by default which is somehow not the logger setup by
    # checksum_helper so specify our logger in the kw param
    caplog.set_level(logging.INFO, logger='Checksum_Helper')
    # ------------ 1 wrong crc, no missing ----------
    hfile_path = os.path.join(test_verify_root, "sub3",
                              "sub2", "sub3_sub2.sha512")
    a = Args(hash_file_name=[hfile_path])
    starting_cwd = os.getcwd()

    caplog.clear()
    # files_total, nr_matches, nr_missing, nr_crc_errors
    assert _cl_verify_hfile(a) == (3, 2, 0, 1)
    # cwd hasn't changed
    assert starting_cwd == os.getcwd()
    x_contains_all_y(caplog.record_tuples, [
        ('Checksum_Helper', logging.WARNING, "Found reference beyond the hash file's root dir in file: '%s'. "
                                             "Consider moving/copying the file using ChecksumHelper move/copy "
                                             "to the path that is the most common denominator!"
                                             % os.path.join(test_verify_root, "sub3", "sub2", "sub3_sub2.sha512")),
        ('Checksum_Helper', logging.INFO, f'..{os.sep}file1.txt: SHA512 OK'),
        ('Checksum_Helper', logging.WARNING,
         f'..{os.sep}sub1{os.sep}file1.txt: SHA512 FAILED'),
        ('Checksum_Helper', logging.INFO, f'file1.txt: SHA512 OK'),
    ])
    assert caplog.record_tuples[4:6] == [
        ('Checksum_Helper', logging.WARNING,
         f'{test_verify_root}{os.sep}sub3{os.sep}sub2{os.sep}sub3_sub2.sha512: 1 files with wrong CRCs!'),
        ('Checksum_Helper', logging.INFO,
         f'{test_verify_root}{os.sep}sub3{os.sep}sub2{os.sep}sub3_sub2.sha512: No missing files!'),
    ]


def test_verify_hfile_warn_missing(caplog):
    test_verify_root = os.path.join(TESTS_DIR, "test_verify_files", "tt")
    # caplog.set_level sets on root logger by default which is somehow not the logger setup by
    # checksum_helper so specify our logger in the kw param
    caplog.set_level(logging.INFO, logger='Checksum_Helper')
    # ------------ all matching, 1 missing ----------
    hfile_path = os.path.join(test_verify_root, "sub1",
                              "sub2", "sub2_1miss.sha512")
    a = Args(hash_file_name=[hfile_path])
    starting_cwd = os.getcwd()

    caplog.clear()
    assert _cl_verify_hfile(a) == (3, 2, 1, 0)
    # cwd hasn't changed
    assert starting_cwd == os.getcwd()
    x_contains_all_y(caplog.record_tuples, [
        ('Checksum_Helper', logging.INFO, f'new 2.txt: SHA512 OK'),
        ('Checksum_Helper', logging.WARNING, f'new 8.txt: MISSING'),
        ('Checksum_Helper', logging.INFO, f'new 4.txt: SHA512 OK'),
    ])
    assert caplog.record_tuples[3:5] == [
        ('Checksum_Helper', logging.INFO,
         f'{test_verify_root}{os.sep}sub1{os.sep}sub2{os.sep}sub2_1miss.sha512: All files matching their hashes!'),
        ('Checksum_Helper', logging.WARNING,
         f'{test_verify_root}{os.sep}sub1{os.sep}sub2{os.sep}sub2_1miss.sha512: 1 missing files!'),
    ]


def test_verify_hfile_successful(caplog):
    test_verify_root = os.path.join(TESTS_DIR, "test_verify_files", "tt")
    # caplog.set_level sets on root logger by default which is somehow not the logger setup by
    # checksum_helper so specify our logger in the kw param
    caplog.set_level(logging.INFO, logger='Checksum_Helper')
    # ----------- no missing all matching ----------
    hfile_path = os.path.join(test_verify_root, "sub1", "sub2", "sub2.sha512")
    a = Args(hash_file_name=[hfile_path])
    starting_cwd = os.getcwd()

    caplog.clear()
    # caplog.set_level sets on root logger by default which is somehow not the logger setup by
    # checksum_helper so specify our logger in the kw param
    assert _cl_verify_hfile(a) == (3, 3, 0, 0)
    # cwd hasn't changed
    assert starting_cwd == os.getcwd()
    x_contains_all_y(caplog.record_tuples, [
        ('Checksum_Helper', logging.INFO, f'new 2.txt: SHA512 OK'),
        ('Checksum_Helper', logging.INFO, f'new 3.txt: SHA512 OK'),
        ('Checksum_Helper', logging.INFO, f'new 4.txt: SHA512 OK'),
    ])
    assert caplog.record_tuples[-3] == ('Checksum_Helper', logging.INFO,
                                        f'{test_verify_root}{os.sep}sub1{os.sep}sub2{os.sep}sub2.sha512: No missing files and all files matching their hashes')


def test_verify_hfile_warn_missing_and_crc(caplog):
    test_verify_root = os.path.join(TESTS_DIR, "test_verify_files", "tt")
    # caplog.set_level sets on root logger by default which is somehow not the logger setup by
    # checksum_helper so specify our logger in the kw param
    caplog.set_level(logging.INFO, logger='Checksum_Helper')
    # ----------- 2 missing 2 crc err ----------
    hfile_path = os.path.join(test_verify_root, "sub1+2_n3+4.sha512")
    a = Args(hash_file_name=[hfile_path])
    starting_cwd = os.getcwd()

    caplog.clear()
    # caplog.set_level sets on root logger by default which is somehow not the logger setup by
    # checksum_helper so specify our logger in the kw param
    assert _cl_verify_hfile(a) == (11, 7, 2, 2)
    # cwd hasn't changed
    assert starting_cwd == os.getcwd()
    x_contains_all_y(caplog.record_tuples, [
        ('Checksum_Helper', logging.WARNING, f'new 3.txt: SHA512 FAILED'),
        ('Checksum_Helper', logging.INFO, f'new 4.txt: SHA512 OK'),
        ('Checksum_Helper', logging.INFO, f'sub1{os.sep}new 2.txt: SHA512 OK'),
        ('Checksum_Helper', logging.INFO, f'sub1{os.sep}new 3.txt: SHA512 OK'),
        ('Checksum_Helper', logging.INFO, f'sub1{os.sep}new 4.txt: SHA512 OK'),
        ('Checksum_Helper', logging.INFO,
         f'sub1{os.sep}sub2{os.sep}new 2.txt: SHA512 OK'),
        ('Checksum_Helper', logging.INFO,
         f'sub1{os.sep}sub2{os.sep}new 3.txt: SHA512 OK'),
        ('Checksum_Helper', logging.WARNING,
         f'sub1{os.sep}sub2{os.sep}new 4.txt: SHA512 FAILED'),
        ('Checksum_Helper', logging.INFO,
         f'sub2{os.sep}sub1{os.sep}file1.txt: SHA512 OK'),
        ('Checksum_Helper', logging.WARNING,
         f'sub5{os.sep}sub1{os.sep}file1.txt: MISSING'),
        ('Checksum_Helper', logging.WARNING,
         f'sub6{os.sep}file1.txt: MISSING'),
    ])
    assert caplog.record_tuples[11:13] == [
        ('Checksum_Helper', logging.WARNING,
         f'{test_verify_root}{os.sep}sub1+2_n3+4.sha512: 2 files with wrong CRCs!'),
        ('Checksum_Helper', logging.WARNING,
         f'{test_verify_root}{os.sep}sub1+2_n3+4.sha512: 2 missing files!'),
    ]


def test_verify_all(caplog):
    test_verify_root = os.path.join(TESTS_DIR, "test_verify_files", "tt")
    # caplog.set_level sets on root logger by default which is somehow not the logger setup by
    # checksum_helper so specify our logger in the kw param
    caplog.set_level(logging.INFO, logger='Checksum_Helper')
    # ------------ 2 wrong crc, 2 missing, MixedAlgo ----------
    root_dir = test_verify_root
    a = Args(root_dir=[root_dir],
             discover_hash_files_depth=1, hash_filename_filter=())

    caplog.clear()
    # files_total, nr_matches, nr_missing, nr_crc_errors
    assert _cl_verify_all(a) == (16, 10, 3, 3)
    x_contains_all_y(caplog.record_tuples, [
        ('Checksum_Helper', logging.INFO, f'new 2.txt: MD5 OK'),
        ('Checksum_Helper', logging.WARNING, f'new 3.txt: SHA512 FAILED'),
        ('Checksum_Helper', logging.INFO, f'new 4.txt: SHA512 OK'),
        ('Checksum_Helper', logging.INFO, f'sub1{os.sep}new 2.txt: SHA512 OK'),
        ('Checksum_Helper', logging.INFO, f'sub1{os.sep}new 3.txt: SHA512 OK'),
        ('Checksum_Helper', logging.INFO, f'sub1{os.sep}new 4.txt: SHA512 OK'),
        ('Checksum_Helper', logging.INFO,
         f'sub1{os.sep}sub2{os.sep}new 2.txt: SHA512 OK'),
        ('Checksum_Helper', logging.INFO,
         f'sub1{os.sep}sub2{os.sep}new 3.txt: SHA512 OK'),
        ('Checksum_Helper', logging.WARNING,
         f'sub1{os.sep}sub2{os.sep}new 4.txt: SHA512 FAILED'),
        ('Checksum_Helper', logging.INFO,
         f'sub2{os.sep}sub1{os.sep}file1.txt: SHA512 OK'),
        ('Checksum_Helper', logging.WARNING,
         f'sub5{os.sep}sub1{os.sep}file1.txt: MISSING'),
        ('Checksum_Helper', logging.WARNING,
         f'sub6{os.sep}file1.txt: MISSING'),
        ('Checksum_Helper', logging.INFO, f'new_cshd.txt: SHA512 OK'),
        ('Checksum_Helper', logging.WARNING,
         f'sub1{os.sep}new_cshd_3.txt: SHA512 FAILED -> OUTDATED HASH (file is newer)'),
        ('Checksum_Helper', logging.WARNING,
         f'sub2{os.sep}new_cshd_missing.txt: MISSING'),
        ('Checksum_Helper', logging.INFO,
         f'sub3{os.sep}sub2{os.sep}new_cshd2.txt: SHA512 OK'),
    ])

    assert caplog.record_tuples[16:18] == [
        ('Checksum_Helper', logging.WARNING,
         f"{root_dir}{os.sep}tt_most_current_{time.strftime('%Y-%m-%d')}.cshd: 3 files with wrong CRCs!"),
        ('Checksum_Helper', logging.WARNING,
         f"{root_dir}{os.sep}tt_most_current_{time.strftime('%Y-%m-%d')}.cshd: 3 missing files!"),
    ]

    # ------------ all matching, 1 missing, most_current single hash file ----------
    root_dir = os.path.join(test_verify_root, "sub1", "sub2")
    a = Args(root_dir=[root_dir], discover_hash_files_depth=0,
             hash_filename_filter=("*.cshd",))

    caplog.clear()
    assert _cl_verify_all(a) == (4, 3, 1, 0)
    x_contains_all_y(caplog.record_tuples, [
        ('Checksum_Helper', logging.INFO, f'new 2.txt: SHA512 OK'),
        ('Checksum_Helper', logging.INFO, f'new 3.txt: SHA512 OK'),
        ('Checksum_Helper', logging.INFO, f'new 4.txt: SHA512 OK'),
        ('Checksum_Helper', logging.WARNING, f'new 8.txt: MISSING'),
    ])
    assert caplog.record_tuples[4:6] == [
        ('Checksum_Helper', logging.INFO,
         f'{root_dir}{os.sep}sub2_most_current_{time.strftime("%Y-%m-%d")}.sha512: All files matching their hashes!'),
        ('Checksum_Helper', logging.WARNING,
         f'{root_dir}{os.sep}sub2_most_current_{time.strftime("%Y-%m-%d")}.sha512: 1 missing files!'),
    ]

    # ------------ 3 wrong crc, 4 missing ----------
    root_dir = test_verify_root
    a = Args(root_dir=[root_dir],
             discover_hash_files_depth=-1, hash_filename_filter=())

    caplog.clear()
    assert _cl_verify_all(a) == (20, 13, 4, 3)
    x_contains_all_y(caplog.record_tuples, [
        ('Checksum_Helper', logging.WARNING, "Found reference beyond the hash file's root dir in file: '%s'. "
                                             "Consider moving/copying the file using ChecksumHelper move/copy "
                                             "to the path that is the most common denominator!"
                                             % os.path.join(root_dir, "sub3", "sub2", "sub3_sub2.sha512")),
        ('Checksum_Helper', logging.INFO, f'new 2.txt: MD5 OK'),
        ('Checksum_Helper', logging.INFO, f'sub3{os.sep}file1.txt: SHA512 OK'),
        ('Checksum_Helper', logging.WARNING,
         f'sub3{os.sep}sub1{os.sep}file1.txt: SHA512 FAILED'),
        ('Checksum_Helper', logging.INFO,
         f'sub3{os.sep}sub2{os.sep}file1.txt: SHA512 OK'),
        ('Checksum_Helper', logging.WARNING, f'new 3.txt: SHA512 FAILED'),
        ('Checksum_Helper', logging.INFO, f'new 4.txt: SHA512 OK'),
        ('Checksum_Helper', logging.INFO, f'sub1{os.sep}new 2.txt: SHA512 OK'),
        ('Checksum_Helper', logging.INFO, f'sub1{os.sep}new 3.txt: SHA512 OK'),
        ('Checksum_Helper', logging.INFO, f'sub1{os.sep}new 4.txt: SHA512 OK'),
        ('Checksum_Helper', logging.INFO,
         f'sub1{os.sep}sub2{os.sep}new 2.txt: SHA512 OK'),
        ('Checksum_Helper', logging.INFO,
         f'sub1{os.sep}sub2{os.sep}new 3.txt: SHA512 OK'),
        ('Checksum_Helper', logging.INFO,
         f'sub1{os.sep}sub2{os.sep}new 4.txt: SHA512 OK'),
        ('Checksum_Helper', logging.INFO,
         f'sub2{os.sep}sub1{os.sep}file1.txt: SHA512 OK'),
        ('Checksum_Helper', logging.WARNING,
         f'sub5{os.sep}sub1{os.sep}file1.txt: MISSING'),
        ('Checksum_Helper', logging.WARNING,
         f'sub6{os.sep}file1.txt: MISSING'),
        ('Checksum_Helper', logging.WARNING,
         f'sub1{os.sep}sub2{os.sep}new 8.txt: MISSING'),
        ('Checksum_Helper', logging.INFO, f'new_cshd.txt: SHA512 OK'),
        ('Checksum_Helper', logging.WARNING,
         f'sub1{os.sep}new_cshd_3.txt: SHA512 FAILED -> OUTDATED HASH (file is newer)'),
        ('Checksum_Helper', logging.WARNING,
         f'sub2{os.sep}new_cshd_missing.txt: MISSING'),
        ('Checksum_Helper', logging.INFO,
         f'sub3{os.sep}sub2{os.sep}new_cshd2.txt: SHA512 OK'),
    ])
    assert caplog.record_tuples[21:23] == [
        ('Checksum_Helper', logging.WARNING,
         f"{root_dir}{os.sep}tt_most_current_{time.strftime('%Y-%m-%d')}.cshd: 3 files with wrong CRCs!"),
        ('Checksum_Helper', logging.WARNING,
         f"{root_dir}{os.sep}tt_most_current_{time.strftime('%Y-%m-%d')}.cshd: 4 missing files!"),
    ]

    # ------------ 2 wrong crc, 3 missing, single hash, md5+cshd filtered  ----------
    root_dir = test_verify_root
    # hash_filename_filter literally only filters out the hashfile if a str of
    # hash_filename_filter is in the name of the file without the extension
    a = Args(root_dir=[root_dir], discover_hash_files_depth=-
             1, hash_filename_filter=("*.md5", "*.cshd"))

    caplog.clear()
    assert _cl_verify_all(a) == (15, 10, 3, 2)
    x_contains_all_y(caplog.record_tuples, [
        ('Checksum_Helper', logging.WARNING, "Found reference beyond the hash file's root dir in file: '%s'. "
                                             "Consider moving/copying the file using ChecksumHelper move/copy "
                                             "to the path that is the most common denominator!"
                                             % os.path.join(root_dir, "sub3", "sub2", "sub3_sub2.sha512")),
        ('Checksum_Helper', logging.INFO, f'sub3{os.sep}file1.txt: SHA512 OK'),
        ('Checksum_Helper', logging.WARNING,
         f'sub3{os.sep}sub1{os.sep}file1.txt: SHA512 FAILED'),
        ('Checksum_Helper', logging.INFO,
         f'sub3{os.sep}sub2{os.sep}file1.txt: SHA512 OK'),
        ('Checksum_Helper', logging.WARNING, f'new 3.txt: SHA512 FAILED'),
        ('Checksum_Helper', logging.INFO, f'new 4.txt: SHA512 OK'),
        ('Checksum_Helper', logging.INFO, f'sub1{os.sep}new 2.txt: SHA512 OK'),
        ('Checksum_Helper', logging.INFO, f'sub1{os.sep}new 3.txt: SHA512 OK'),
        ('Checksum_Helper', logging.INFO, f'sub1{os.sep}new 4.txt: SHA512 OK'),
        ('Checksum_Helper', logging.INFO,
         f'sub1{os.sep}sub2{os.sep}new 2.txt: SHA512 OK'),
        ('Checksum_Helper', logging.INFO,
         f'sub1{os.sep}sub2{os.sep}new 3.txt: SHA512 OK'),
        ('Checksum_Helper', logging.INFO,
         f'sub1{os.sep}sub2{os.sep}new 4.txt: SHA512 OK'),
        ('Checksum_Helper', logging.INFO,
         f'sub2{os.sep}sub1{os.sep}file1.txt: SHA512 OK'),
        ('Checksum_Helper', logging.WARNING,
         f'sub5{os.sep}sub1{os.sep}file1.txt: MISSING'),
        ('Checksum_Helper', logging.WARNING,
         f'sub6{os.sep}file1.txt: MISSING'),
        ('Checksum_Helper', logging.WARNING,
         f'sub1{os.sep}sub2{os.sep}new 8.txt: MISSING'),
    ])

    assert caplog.record_tuples[16:18] == [
        ('Checksum_Helper', logging.WARNING,
         f"{root_dir}{os.sep}tt_most_current_{time.strftime('%Y-%m-%d')}.sha512: 2 files with wrong CRCs!"),
        ('Checksum_Helper', logging.WARNING,
         f"{root_dir}{os.sep}tt_most_current_{time.strftime('%Y-%m-%d')}.sha512: 3 missing files!"),
    ]


def test_verify_filter(caplog):
    test_verify_root = os.path.join(TESTS_DIR, "test_verify_files", "tt")
    # caplog.set_level sets on root logger by default which is somehow not the logger setup by
    # checksum_helper so specify our logger in the kw param
    caplog.set_level(logging.INFO, logger='Checksum_Helper')
    # ------------ 3 wrong crc, no missing, MixedAlgo ----------
    root_dir = test_verify_root
    a = Args(root_dir=root_dir, discover_hash_files_depth=1, hash_filename_filter=(),
             filter=[
                 f"sub1{os.sep}*",
                 "new ?.txt",
    ])

    caplog.clear()
    _cl_verify_filter(a)
    x_contains_all_y(caplog.record_tuples, [
        ('Checksum_Helper', logging.INFO, f'new 2.txt: MD5 OK'),
        ('Checksum_Helper', logging.WARNING, f'new 3.txt: SHA512 FAILED'),
        ('Checksum_Helper', logging.INFO, f'new 4.txt: SHA512 OK'),
        ('Checksum_Helper', logging.INFO, f'sub1{os.sep}new 2.txt: SHA512 OK'),
        ('Checksum_Helper', logging.INFO, f'sub1{os.sep}new 3.txt: SHA512 OK'),
        ('Checksum_Helper', logging.INFO, f'sub1{os.sep}new 4.txt: SHA512 OK'),
        ('Checksum_Helper', logging.INFO,
         f'sub1{os.sep}sub2{os.sep}new 2.txt: SHA512 OK'),
        ('Checksum_Helper', logging.INFO,
         f'sub1{os.sep}sub2{os.sep}new 3.txt: SHA512 OK'),
        ('Checksum_Helper', logging.WARNING,
         f'sub1{os.sep}sub2{os.sep}new 4.txt: SHA512 FAILED'),
        ('Checksum_Helper', logging.WARNING,
         f'sub1{os.sep}new_cshd_3.txt: SHA512 FAILED -> OUTDATED HASH (file is newer)'),
    ])

    assert caplog.record_tuples[10:12] == [
        ('Checksum_Helper', logging.WARNING,
         f"{root_dir}{os.sep}tt_most_current_{time.strftime('%Y-%m-%d')}.cshd: 3 files with wrong CRCs!"),
        ('Checksum_Helper', logging.INFO,
         f"{root_dir}{os.sep}tt_most_current_{time.strftime('%Y-%m-%d')}.cshd: No missing files!"),
    ]

    # ------------ 1 crc err, 2 missing, MixedAlgo ----------
    root_dir = test_verify_root
    a = Args(root_dir=root_dir, discover_hash_files_depth=-1, hash_filename_filter=(),
             filter=[
                 "*file?.txt",
                 f"s*{os.sep}sub1{os.sep}**",
    ])

    caplog.clear()
    _cl_verify_filter(a)
    x_contains_all_y(caplog.record_tuples, [
        ('Checksum_Helper', logging.WARNING, "Found reference beyond the hash file's root dir in file: '%s'. "
                                             "Consider moving/copying the file using ChecksumHelper move/copy "
                                             "to the path that is the most common denominator!"
                                             % os.path.join(root_dir, "sub3", "sub2", "sub3_sub2.sha512")),
        ('Checksum_Helper', logging.INFO, f'sub3{os.sep}file1.txt: SHA512 OK'),
        ('Checksum_Helper', logging.WARNING,
         f'sub3{os.sep}sub1{os.sep}file1.txt: SHA512 FAILED'),
        ('Checksum_Helper', logging.INFO,
         f'sub3{os.sep}sub2{os.sep}file1.txt: SHA512 OK'),
        ('Checksum_Helper', logging.INFO,
         f'sub2{os.sep}sub1{os.sep}file1.txt: SHA512 OK'),
        ('Checksum_Helper', logging.WARNING,
         f'sub5{os.sep}sub1{os.sep}file1.txt: MISSING'),
        ('Checksum_Helper', logging.WARNING,
         f'sub6{os.sep}file1.txt: MISSING'),
    ])

    assert caplog.record_tuples[7:9] == [
        ('Checksum_Helper', logging.WARNING,
         f"{root_dir}{os.sep}tt_most_current_{time.strftime('%Y-%m-%d')}.cshd: 1 files with wrong CRCs!"),
        ('Checksum_Helper', logging.WARNING,
         f"{root_dir}{os.sep}tt_most_current_{time.strftime('%Y-%m-%d')}.cshd: 2 missing files!"),
    ]

    # ------------ 2 wrong crc, 4 missing, HashFile, md5 filtered  ----------
    root_dir = test_verify_root
    # hash_filename_filter literally only filters out the hashfile if a str of
    # hash_filename_filter is in the name of the file without the extension
    a = Args(root_dir=root_dir, discover_hash_files_depth=-1, hash_filename_filter=("*.md5",),
             filter=[
                 "",
                 f"sub?{os.sep}*",
    ])

    caplog.clear()
    _cl_verify_filter(a)
    x_contains_all_y(caplog.record_tuples, [
        ('Checksum_Helper', logging.WARNING, "Found reference beyond the hash file's root dir in file: '%s'. "
                                             "Consider moving/copying the file using ChecksumHelper move/copy "
                                             "to the path that is the most common denominator!"
                                             % os.path.join(root_dir, "sub3", "sub2", "sub3_sub2.sha512")),
        ('Checksum_Helper', logging.INFO, f'sub3{os.sep}file1.txt: SHA512 OK'),
        ('Checksum_Helper', logging.WARNING,
         f'sub3{os.sep}sub1{os.sep}file1.txt: SHA512 FAILED'),
        ('Checksum_Helper', logging.INFO,
         f'sub3{os.sep}sub2{os.sep}file1.txt: SHA512 OK'),
        ('Checksum_Helper', logging.INFO, f'sub1{os.sep}new 2.txt: SHA512 OK'),
        ('Checksum_Helper', logging.INFO, f'sub1{os.sep}new 3.txt: SHA512 OK'),
        ('Checksum_Helper', logging.INFO, f'sub1{os.sep}new 4.txt: SHA512 OK'),
        ('Checksum_Helper', logging.INFO,
         f'sub1{os.sep}sub2{os.sep}new 2.txt: SHA512 OK'),
        ('Checksum_Helper', logging.INFO,
         f'sub1{os.sep}sub2{os.sep}new 3.txt: SHA512 OK'),
        ('Checksum_Helper', logging.INFO,
         f'sub1{os.sep}sub2{os.sep}new 4.txt: SHA512 OK'),
        ('Checksum_Helper', logging.INFO,
         f'sub2{os.sep}sub1{os.sep}file1.txt: SHA512 OK'),
        ('Checksum_Helper', logging.WARNING,
         f'sub5{os.sep}sub1{os.sep}file1.txt: MISSING'),
        ('Checksum_Helper', logging.WARNING,
         f'sub6{os.sep}file1.txt: MISSING'),
        ('Checksum_Helper', logging.WARNING,
         f'sub1{os.sep}sub2{os.sep}new 8.txt: MISSING'),
        ('Checksum_Helper', logging.WARNING,
         f'sub1{os.sep}new_cshd_3.txt: SHA512 FAILED -> OUTDATED HASH (file is newer)'),
        ('Checksum_Helper', logging.WARNING,
         f'sub2{os.sep}new_cshd_missing.txt: MISSING'),
        ('Checksum_Helper', logging.INFO,
         f'sub3{os.sep}sub2{os.sep}new_cshd2.txt: SHA512 OK'),
    ])

    assert caplog.record_tuples[17:19] == [
        ('Checksum_Helper', logging.WARNING,
         f"{root_dir}{os.sep}tt_most_current_{time.strftime('%Y-%m-%d')}.cshd: 2 files with wrong CRCs!"),
        ('Checksum_Helper', logging.WARNING,
         f"{root_dir}{os.sep}tt_most_current_{time.strftime('%Y-%m-%d')}.cshd: 4 missing files!"),
    ]

    # ------------ 1 wrong crc, 1 missing, HashFile, md5 filtered  ----------
    root_dir = test_verify_root
    # hash_filename_filter literally only filters out the hashfile if a str of
    # hash_filename_filter is in the name of the file without the extension
    a = Args(root_dir=root_dir, discover_hash_files_depth=-1, hash_filename_filter=("*.md5",),
             filter=[
                 "*new* ?.txt",
    ])

    caplog.clear()
    _cl_verify_filter(a)
    x_contains_all_y(caplog.record_tuples, [
        ('Checksum_Helper', logging.WARNING, "Found reference beyond the hash file's root dir in file: '%s'. "
                                             "Consider moving/copying the file using ChecksumHelper move/copy "
                                             "to the path that is the most common denominator!"
                                             % os.path.join(root_dir, "sub3", "sub2", "sub3_sub2.sha512")),
        ('Checksum_Helper', logging.WARNING, f'new 3.txt: SHA512 FAILED'),
        ('Checksum_Helper', logging.INFO, f'new 4.txt: SHA512 OK'),
        ('Checksum_Helper', logging.INFO, f'sub1{os.sep}new 2.txt: SHA512 OK'),
        ('Checksum_Helper', logging.INFO, f'sub1{os.sep}new 3.txt: SHA512 OK'),
        ('Checksum_Helper', logging.INFO, f'sub1{os.sep}new 4.txt: SHA512 OK'),
        ('Checksum_Helper', logging.INFO,
         f'sub1{os.sep}sub2{os.sep}new 2.txt: SHA512 OK'),
        ('Checksum_Helper', logging.INFO,
         f'sub1{os.sep}sub2{os.sep}new 3.txt: SHA512 OK'),
        ('Checksum_Helper', logging.INFO,
         f'sub1{os.sep}sub2{os.sep}new 4.txt: SHA512 OK'),
        ('Checksum_Helper', logging.WARNING,
         f'sub1{os.sep}sub2{os.sep}new 8.txt: MISSING'),
    ])

    assert caplog.record_tuples[10:12] == [
        ('Checksum_Helper', logging.WARNING,
         f"{root_dir}{os.sep}tt_most_current_{time.strftime('%Y-%m-%d')}.cshd: 1 files with wrong CRCs!"),
        ('Checksum_Helper', logging.WARNING,
         f"{root_dir}{os.sep}tt_most_current_{time.strftime('%Y-%m-%d')}.cshd: 1 missing files!"),
    ]
