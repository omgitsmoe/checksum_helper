import os
import logging
import time

from utils import TESTS_DIR, Args

from checksum_helper import ChecksumHelper, _cl_verify_hfile, _cl_verify_all, _cl_verify_filter


def x_contains_all_y(x, y) -> bool:
    for yy in y:
        if yy in x:
            continue
        else:
            return False
    return True


def test_verify_cshd(caplog):
    test_verify_root = os.path.join(TESTS_DIR, "test_verify_files", "tt")
    # caplog.set_level sets on root logger by default which is somehow not the logger setup by
    # checksum_helper so specify our logger in the kw param
    caplog.set_level(logging.INFO, logger='Checksum_Helper')
    # ------------ 1 wrong crc, 1 missing ----------
    hfile_path = os.path.join(test_verify_root, "new_cshd_1+3+missing.cshd")
    a = Args(hash_file_name=[hfile_path])
    starting_cwd = os.getcwd()

    caplog.clear()
    # files_total, nr_matches, nr_missing, nr_crc_errors
    assert _cl_verify_hfile(a) == (3, 1, 1, 1)
    # cwd hasn't changed
    assert starting_cwd == os.getcwd()
    assert x_contains_all_y(caplog.record_tuples, [
        ('Checksum_Helper', logging.INFO, f'new_cshd.txt: SHA512 OK'),
        ('Checksum_Helper', logging.WARNING, f'sub1{os.sep}new_cshd_3.txt: SHA512 FAILED'),
        ('Checksum_Helper', logging.WARNING, f'sub2{os.sep}new_cshd_missing.txt: MISSING'),
    ])

    assert caplog.record_tuples[3:] == [
        ('Checksum_Helper', logging.WARNING, f'{test_verify_root}{os.sep}new_cshd_1+3+missing.cshd: 1 files with wrong CRCs!'),
        ('Checksum_Helper', logging.WARNING, f'{test_verify_root}{os.sep}new_cshd_1+3+missing.cshd: 1 missing files!'),
    ]

def test_verify_hfile(caplog):
    test_verify_root = os.path.join(TESTS_DIR, "test_verify_files", "tt")
    # caplog.set_level sets on root logger by default which is somehow not the logger setup by
    # checksum_helper so specify our logger in the kw param
    caplog.set_level(logging.INFO, logger='Checksum_Helper')
    # ------------ 1 wrong crc, no missing ----------
    hfile_path = os.path.join(test_verify_root, "sub3", "sub2", "sub3_sub2.sha512")
    a = Args(hash_file_name=[hfile_path])
    starting_cwd = os.getcwd()

    caplog.clear()
    # files_total, nr_matches, nr_missing, nr_crc_errors
    assert _cl_verify_hfile(a) == (3, 2, 0, 1)
    # cwd hasn't changed
    assert starting_cwd == os.getcwd()
    assert x_contains_all_y(caplog.record_tuples, [
        ('Checksum_Helper', logging.WARNING, "Found reference beyond the hash file's root dir in file: '%s'. "
                                             "Consider moving/copying the file using ChecksumHelper move/copy "
                                             "to the path that is the most common denominator!"
                                             % os.path.join(test_verify_root, "sub3", "sub2", "sub3_sub2.sha512")),
        ('Checksum_Helper', logging.INFO, f'..{os.sep}file1.txt: SHA512 OK'),
        ('Checksum_Helper', logging.WARNING, f'..{os.sep}sub1{os.sep}file1.txt: SHA512 FAILED'),
        ('Checksum_Helper', logging.INFO, f'file1.txt: SHA512 OK'),
    ])
    assert caplog.record_tuples[4:] == [
        ('Checksum_Helper', logging.WARNING, f'{test_verify_root}{os.sep}sub3{os.sep}sub2{os.sep}sub3_sub2.sha512: 1 files with wrong CRCs!'),
        ('Checksum_Helper', logging.INFO, f'{test_verify_root}{os.sep}sub3{os.sep}sub2{os.sep}sub3_sub2.sha512: No missing files!'),
    ]

    # ------------ all matching, 1 missing ----------
    hfile_path = os.path.join(test_verify_root, "sub1", "sub2", "sub2_1miss.sha512")
    a = Args(hash_file_name=[hfile_path])
    starting_cwd = os.getcwd()

    caplog.clear()
    assert _cl_verify_hfile(a) == (3, 2, 1, 0)
    # cwd hasn't changed
    assert starting_cwd == os.getcwd()
    assert x_contains_all_y(caplog.record_tuples, [
        ('Checksum_Helper', logging.INFO, f'new 2.txt: SHA512 OK'),
        ('Checksum_Helper', logging.WARNING, f'new 8.txt: MISSING'),
        ('Checksum_Helper', logging.INFO, f'new 4.txt: SHA512 OK'),
    ])
    assert caplog.record_tuples[3:] == [
        ('Checksum_Helper', logging.INFO, f'{test_verify_root}{os.sep}sub1{os.sep}sub2{os.sep}sub2_1miss.sha512: All files matching their hashes!'),
        ('Checksum_Helper', logging.WARNING, f'{test_verify_root}{os.sep}sub1{os.sep}sub2{os.sep}sub2_1miss.sha512: 1 missing files!'),
    ]

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
    assert x_contains_all_y(caplog.record_tuples, [
        ('Checksum_Helper', logging.INFO, f'new 2.txt: SHA512 OK'),
        ('Checksum_Helper', logging.INFO, f'new 3.txt: SHA512 OK'),
        ('Checksum_Helper', logging.INFO, f'new 4.txt: SHA512 OK'),
    ])
    assert caplog.record_tuples[-1] == ('Checksum_Helper', logging.INFO, f'{test_verify_root}{os.sep}sub1{os.sep}sub2{os.sep}sub2.sha512: No missing files and all files matching their hashes')

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
    assert x_contains_all_y(caplog.record_tuples, [
        ('Checksum_Helper', logging.WARNING, f'new 3.txt: SHA512 FAILED'),
        ('Checksum_Helper', logging.INFO, f'new 4.txt: SHA512 OK'),
        ('Checksum_Helper', logging.INFO, f'sub1{os.sep}new 2.txt: SHA512 OK'),
        ('Checksum_Helper', logging.INFO, f'sub1{os.sep}new 3.txt: SHA512 OK'),
        ('Checksum_Helper', logging.INFO, f'sub1{os.sep}new 4.txt: SHA512 OK'),
        ('Checksum_Helper', logging.INFO, f'sub1{os.sep}sub2{os.sep}new 2.txt: SHA512 OK'),
        ('Checksum_Helper', logging.INFO, f'sub1{os.sep}sub2{os.sep}new 3.txt: SHA512 OK'),
        ('Checksum_Helper', logging.WARNING, f'sub1{os.sep}sub2{os.sep}new 4.txt: SHA512 FAILED'),
        ('Checksum_Helper', logging.INFO, f'sub2{os.sep}sub1{os.sep}file1.txt: SHA512 OK'),
        ('Checksum_Helper', logging.WARNING, f'sub5{os.sep}sub1{os.sep}file1.txt: MISSING'),
        ('Checksum_Helper', logging.WARNING, f'sub6{os.sep}file1.txt: MISSING'),
    ])
    assert caplog.record_tuples[11:] == [
        ('Checksum_Helper', logging.WARNING, f'{test_verify_root}{os.sep}sub1+2_n3+4.sha512: 2 files with wrong CRCs!'),
        ('Checksum_Helper', logging.WARNING, f'{test_verify_root}{os.sep}sub1+2_n3+4.sha512: 2 missing files!'),
    ]


def test_verify_all(caplog):
    test_verify_root = os.path.join(TESTS_DIR, "test_verify_files", "tt")
    # caplog.set_level sets on root logger by default which is somehow not the logger setup by
    # checksum_helper so specify our logger in the kw param
    caplog.set_level(logging.INFO, logger='Checksum_Helper')
    # ------------ 2 wrong crc, 2 missing, MixedAlgo ----------
    root_dir = test_verify_root
    a = Args(root_dir=[root_dir], discover_hash_files_depth=1, hash_filename_filter=())

    caplog.clear()
    # files_total, nr_matches, nr_missing, nr_crc_errors
    assert _cl_verify_all(a) == (16, 10, 3, 3)
    assert x_contains_all_y(caplog.record_tuples, [
        ('Checksum_Helper', logging.INFO, f'new 2.txt: MD5 OK'),
        ('Checksum_Helper', logging.WARNING, f'new 3.txt: SHA512 FAILED'),
        ('Checksum_Helper', logging.INFO, f'new 4.txt: SHA512 OK'),
        ('Checksum_Helper', logging.INFO, f'sub1{os.sep}new 2.txt: SHA512 OK'),
        ('Checksum_Helper', logging.INFO, f'sub1{os.sep}new 3.txt: SHA512 OK'),
        ('Checksum_Helper', logging.INFO, f'sub1{os.sep}new 4.txt: SHA512 OK'),
        ('Checksum_Helper', logging.INFO, f'sub1{os.sep}sub2{os.sep}new 2.txt: SHA512 OK'),
        ('Checksum_Helper', logging.INFO, f'sub1{os.sep}sub2{os.sep}new 3.txt: SHA512 OK'),
        ('Checksum_Helper', logging.WARNING, f'sub1{os.sep}sub2{os.sep}new 4.txt: SHA512 FAILED'),
        ('Checksum_Helper', logging.INFO, f'sub2{os.sep}sub1{os.sep}file1.txt: SHA512 OK'),
        ('Checksum_Helper', logging.WARNING, f'sub5{os.sep}sub1{os.sep}file1.txt: MISSING'),
        ('Checksum_Helper', logging.WARNING, f'sub6{os.sep}file1.txt: MISSING'),
        ('Checksum_Helper', logging.INFO, f'new_cshd.txt: SHA512 OK'),
        ('Checksum_Helper', logging.WARNING, f'sub1{os.sep}new_cshd_3.txt: SHA512 FAILED'),
        ('Checksum_Helper', logging.WARNING, f'sub2{os.sep}new_cshd_missing.txt: MISSING'),
        ('Checksum_Helper', logging.INFO, f'sub3{os.sep}sub2{os.sep}new_cshd2.txt: SHA512 OK'),
    ])
        
    assert caplog.record_tuples[16:] == [
        ('Checksum_Helper', logging.WARNING, f"{root_dir}{os.sep}tt_most_current_{time.strftime('%Y-%m-%d')}.cshd: 3 files with wrong CRCs!"),
        ('Checksum_Helper', logging.WARNING, f"{root_dir}{os.sep}tt_most_current_{time.strftime('%Y-%m-%d')}.cshd: 3 missing files!"),
    ]

    # ------------ all matching, 1 missing, most_current single hash file ----------
    root_dir = os.path.join(test_verify_root, "sub1", "sub2")
    a = Args(root_dir=[root_dir], discover_hash_files_depth=0, hash_filename_filter=("*.cshd",))

    caplog.clear()
    assert _cl_verify_all(a) == (4, 3, 1, 0)
    assert x_contains_all_y(caplog.record_tuples, [
        ('Checksum_Helper', logging.INFO, f'new 2.txt: SHA512 OK'),
        ('Checksum_Helper', logging.INFO, f'new 3.txt: SHA512 OK'),
        ('Checksum_Helper', logging.INFO, f'new 4.txt: SHA512 OK'),
        ('Checksum_Helper', logging.WARNING, f'new 8.txt: MISSING'),
    ])
    assert caplog.record_tuples[4:] == [
        ('Checksum_Helper', logging.INFO, f'{root_dir}{os.sep}sub2_most_current_{time.strftime("%Y-%m-%d")}.sha512: All files matching their hashes!'),
        ('Checksum_Helper', logging.WARNING, f'{root_dir}{os.sep}sub2_most_current_{time.strftime("%Y-%m-%d")}.sha512: 1 missing files!'),
    ]

    # ------------ 3 wrong crc, 4 missing ----------
    root_dir = test_verify_root
    a = Args(root_dir=[root_dir], discover_hash_files_depth=-1, hash_filename_filter=())

    caplog.clear()
    assert _cl_verify_all(a) == (20, 13, 4, 3)
    assert x_contains_all_y(caplog.record_tuples, [
        ('Checksum_Helper', logging.WARNING, "Found reference beyond the hash file's root dir in file: '%s'. "
                                             "Consider moving/copying the file using ChecksumHelper move/copy "
                                             "to the path that is the most common denominator!"
                                             % os.path.join(root_dir, "sub3", "sub2", "sub3_sub2.sha512")),
        ('Checksum_Helper', logging.INFO, f'new 2.txt: MD5 OK'),
        ('Checksum_Helper', logging.INFO, f'sub3{os.sep}file1.txt: SHA512 OK'),
        ('Checksum_Helper', logging.WARNING, f'sub3{os.sep}sub1{os.sep}file1.txt: SHA512 FAILED'),
        ('Checksum_Helper', logging.INFO, f'sub3{os.sep}sub2{os.sep}file1.txt: SHA512 OK'),
        ('Checksum_Helper', logging.WARNING, f'new 3.txt: SHA512 FAILED'),
        ('Checksum_Helper', logging.INFO, f'new 4.txt: SHA512 OK'),
        ('Checksum_Helper', logging.INFO, f'sub1{os.sep}new 2.txt: SHA512 OK'),
        ('Checksum_Helper', logging.INFO, f'sub1{os.sep}new 3.txt: SHA512 OK'),
        ('Checksum_Helper', logging.INFO, f'sub1{os.sep}new 4.txt: SHA512 OK'),
        ('Checksum_Helper', logging.INFO, f'sub1{os.sep}sub2{os.sep}new 2.txt: SHA512 OK'),
        ('Checksum_Helper', logging.INFO, f'sub1{os.sep}sub2{os.sep}new 3.txt: SHA512 OK'),
        ('Checksum_Helper', logging.INFO, f'sub1{os.sep}sub2{os.sep}new 4.txt: SHA512 OK'),
        ('Checksum_Helper', logging.INFO, f'sub2{os.sep}sub1{os.sep}file1.txt: SHA512 OK'),
        ('Checksum_Helper', logging.WARNING, f'sub5{os.sep}sub1{os.sep}file1.txt: MISSING'),
        ('Checksum_Helper', logging.WARNING, f'sub6{os.sep}file1.txt: MISSING'),
        ('Checksum_Helper', logging.WARNING, f'sub1{os.sep}sub2{os.sep}new 8.txt: MISSING'),
        ('Checksum_Helper', logging.INFO, f'new_cshd.txt: SHA512 OK'),
        ('Checksum_Helper', logging.WARNING, f'sub1{os.sep}new_cshd_3.txt: SHA512 FAILED'),
        ('Checksum_Helper', logging.WARNING, f'sub2{os.sep}new_cshd_missing.txt: MISSING'),
        ('Checksum_Helper', logging.INFO, f'sub3{os.sep}sub2{os.sep}new_cshd2.txt: SHA512 OK'),
    ])
    assert caplog.record_tuples[21:] == [
        ('Checksum_Helper', logging.WARNING, f"{root_dir}{os.sep}tt_most_current_{time.strftime('%Y-%m-%d')}.cshd: 3 files with wrong CRCs!"),
        ('Checksum_Helper', logging.WARNING, f"{root_dir}{os.sep}tt_most_current_{time.strftime('%Y-%m-%d')}.cshd: 4 missing files!"),
    ]

    # ------------ 2 wrong crc, 3 missing, single hash, md5+cshd filtered  ----------
    root_dir = test_verify_root
    # hash_filename_filter literally only filters out the hashfile if a str of
    # hash_filename_filter is in the name of the file without the extension
    a = Args(root_dir=[root_dir], discover_hash_files_depth=-1, hash_filename_filter=("*.md5", "*.cshd"))

    caplog.clear()
    assert _cl_verify_all(a) == (15, 10, 3, 2)
    assert x_contains_all_y(caplog.record_tuples, [
        ('Checksum_Helper', logging.WARNING, "Found reference beyond the hash file's root dir in file: '%s'. "
                                             "Consider moving/copying the file using ChecksumHelper move/copy "
                                             "to the path that is the most common denominator!"
                                             % os.path.join(root_dir, "sub3", "sub2", "sub3_sub2.sha512")),
        ('Checksum_Helper', logging.INFO, f'sub3{os.sep}file1.txt: SHA512 OK'),
        ('Checksum_Helper', logging.WARNING, f'sub3{os.sep}sub1{os.sep}file1.txt: SHA512 FAILED'),
        ('Checksum_Helper', logging.INFO, f'sub3{os.sep}sub2{os.sep}file1.txt: SHA512 OK'),
        ('Checksum_Helper', logging.WARNING, f'new 3.txt: SHA512 FAILED'),
        ('Checksum_Helper', logging.INFO, f'new 4.txt: SHA512 OK'),
        ('Checksum_Helper', logging.INFO, f'sub1{os.sep}new 2.txt: SHA512 OK'),
        ('Checksum_Helper', logging.INFO, f'sub1{os.sep}new 3.txt: SHA512 OK'),
        ('Checksum_Helper', logging.INFO, f'sub1{os.sep}new 4.txt: SHA512 OK'),
        ('Checksum_Helper', logging.INFO, f'sub1{os.sep}sub2{os.sep}new 2.txt: SHA512 OK'),
        ('Checksum_Helper', logging.INFO, f'sub1{os.sep}sub2{os.sep}new 3.txt: SHA512 OK'),
        ('Checksum_Helper', logging.INFO, f'sub1{os.sep}sub2{os.sep}new 4.txt: SHA512 OK'),
        ('Checksum_Helper', logging.INFO, f'sub2{os.sep}sub1{os.sep}file1.txt: SHA512 OK'),
        ('Checksum_Helper', logging.WARNING, f'sub5{os.sep}sub1{os.sep}file1.txt: MISSING'),
        ('Checksum_Helper', logging.WARNING, f'sub6{os.sep}file1.txt: MISSING'),
        ('Checksum_Helper', logging.WARNING, f'sub1{os.sep}sub2{os.sep}new 8.txt: MISSING'),
    ])

    assert caplog.record_tuples[16:] == [
        ('Checksum_Helper', logging.WARNING, f"{root_dir}{os.sep}tt_most_current_{time.strftime('%Y-%m-%d')}.sha512: 2 files with wrong CRCs!"),
        ('Checksum_Helper', logging.WARNING, f"{root_dir}{os.sep}tt_most_current_{time.strftime('%Y-%m-%d')}.sha512: 3 missing files!"),
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
                 f"sub1{os.altsep}*",
                 "new ?.txt",
                    ])

    caplog.clear()
    _cl_verify_filter(a)
    assert x_contains_all_y(caplog.record_tuples, [
        ('Checksum_Helper', logging.INFO, f'new 2.txt: MD5 OK'),
        ('Checksum_Helper', logging.WARNING, f'new 3.txt: SHA512 FAILED'),
        ('Checksum_Helper', logging.INFO, f'new 4.txt: SHA512 OK'),
        ('Checksum_Helper', logging.INFO, f'sub1{os.sep}new 2.txt: SHA512 OK'),
        ('Checksum_Helper', logging.INFO, f'sub1{os.sep}new 3.txt: SHA512 OK'),
        ('Checksum_Helper', logging.INFO, f'sub1{os.sep}new 4.txt: SHA512 OK'),
        ('Checksum_Helper', logging.INFO, f'sub1{os.sep}sub2{os.sep}new 2.txt: SHA512 OK'),
        ('Checksum_Helper', logging.INFO, f'sub1{os.sep}sub2{os.sep}new 3.txt: SHA512 OK'),
        ('Checksum_Helper', logging.WARNING, f'sub1{os.sep}sub2{os.sep}new 4.txt: SHA512 FAILED'),
        ('Checksum_Helper', logging.WARNING, f'sub1{os.sep}new_cshd_3.txt: SHA512 FAILED'),
    ])

    assert caplog.record_tuples[10:] == [
        ('Checksum_Helper', logging.WARNING, f"{root_dir}{os.sep}tt_most_current_{time.strftime('%Y-%m-%d')}.cshd: 3 files with wrong CRCs!"),
        ('Checksum_Helper', logging.INFO, f"{root_dir}{os.sep}tt_most_current_{time.strftime('%Y-%m-%d')}.cshd: No missing files!"),
    ]

    # ------------ 1 crc err, 2 missing, MixedAlgo ----------
    root_dir = test_verify_root
    a = Args(root_dir=root_dir, discover_hash_files_depth=-1, hash_filename_filter=(),
             filter=[
                 "*file?.txt",
                 f"s*{os.altsep}sub1{os.altsep}**",
                    ])

    caplog.clear()
    _cl_verify_filter(a)
    assert x_contains_all_y(caplog.record_tuples, [
        ('Checksum_Helper', logging.WARNING, "Found reference beyond the hash file's root dir in file: '%s'. "
                                             "Consider moving/copying the file using ChecksumHelper move/copy "
                                             "to the path that is the most common denominator!"
                                             % os.path.join(root_dir, "sub3", "sub2", "sub3_sub2.sha512")),
        ('Checksum_Helper', logging.INFO, f'sub3{os.sep}file1.txt: SHA512 OK'),
        ('Checksum_Helper', logging.WARNING, f'sub3{os.sep}sub1{os.sep}file1.txt: SHA512 FAILED'),
        ('Checksum_Helper', logging.INFO, f'sub3{os.sep}sub2{os.sep}file1.txt: SHA512 OK'),
        ('Checksum_Helper', logging.INFO, f'sub2{os.sep}sub1{os.sep}file1.txt: SHA512 OK'),
        ('Checksum_Helper', logging.WARNING, f'sub5{os.sep}sub1{os.sep}file1.txt: MISSING'),
        ('Checksum_Helper', logging.WARNING, f'sub6{os.sep}file1.txt: MISSING'),
    ])

    assert caplog.record_tuples[7:] == [
        ('Checksum_Helper', logging.WARNING, f"{root_dir}{os.sep}tt_most_current_{time.strftime('%Y-%m-%d')}.cshd: 1 files with wrong CRCs!"),
        ('Checksum_Helper', logging.WARNING, f"{root_dir}{os.sep}tt_most_current_{time.strftime('%Y-%m-%d')}.cshd: 2 missing files!"),
    ]

    # ------------ 2 wrong crc, 4 missing, HashFile, md5 filtered  ----------
    root_dir = test_verify_root
    # hash_filename_filter literally only filters out the hashfile if a str of
    # hash_filename_filter is in the name of the file without the extension
    a = Args(root_dir=root_dir, discover_hash_files_depth=-1, hash_filename_filter=("*.md5",),
             filter=[
                 "",
                 f"sub?{os.altsep}*",
                    ])

    caplog.clear()
    _cl_verify_filter(a)
    assert x_contains_all_y(caplog.record_tuples, [
        ('Checksum_Helper', logging.WARNING, "Found reference beyond the hash file's root dir in file: '%s'. "
                                             "Consider moving/copying the file using ChecksumHelper move/copy "
                                             "to the path that is the most common denominator!"
                                             % os.path.join(root_dir, "sub3", "sub2", "sub3_sub2.sha512")),
        ('Checksum_Helper', logging.INFO, f'sub3{os.sep}file1.txt: SHA512 OK'),
        ('Checksum_Helper', logging.WARNING, f'sub3{os.sep}sub1{os.sep}file1.txt: SHA512 FAILED'),
        ('Checksum_Helper', logging.INFO, f'sub3{os.sep}sub2{os.sep}file1.txt: SHA512 OK'),
        ('Checksum_Helper', logging.INFO, f'sub1{os.sep}new 2.txt: SHA512 OK'),
        ('Checksum_Helper', logging.INFO, f'sub1{os.sep}new 3.txt: SHA512 OK'),
        ('Checksum_Helper', logging.INFO, f'sub1{os.sep}new 4.txt: SHA512 OK'),
        ('Checksum_Helper', logging.INFO, f'sub1{os.sep}sub2{os.sep}new 2.txt: SHA512 OK'),
        ('Checksum_Helper', logging.INFO, f'sub1{os.sep}sub2{os.sep}new 3.txt: SHA512 OK'),
        ('Checksum_Helper', logging.INFO, f'sub1{os.sep}sub2{os.sep}new 4.txt: SHA512 OK'),
        ('Checksum_Helper', logging.INFO, f'sub2{os.sep}sub1{os.sep}file1.txt: SHA512 OK'),
        ('Checksum_Helper', logging.WARNING, f'sub5{os.sep}sub1{os.sep}file1.txt: MISSING'),
        ('Checksum_Helper', logging.WARNING, f'sub6{os.sep}file1.txt: MISSING'),
        ('Checksum_Helper', logging.WARNING, f'sub1{os.sep}sub2{os.sep}new 8.txt: MISSING'),
        ('Checksum_Helper', logging.WARNING, f'sub1{os.sep}new_cshd_3.txt: SHA512 FAILED'),
        ('Checksum_Helper', logging.WARNING, f'sub2{os.sep}new_cshd_missing.txt: MISSING'),
        ('Checksum_Helper', logging.INFO, f'sub3{os.sep}sub2{os.sep}new_cshd2.txt: SHA512 OK'),
    ])

    assert caplog.record_tuples[17:] == [
        ('Checksum_Helper', logging.WARNING, f"{root_dir}{os.sep}tt_most_current_{time.strftime('%Y-%m-%d')}.cshd: 2 files with wrong CRCs!"),
        ('Checksum_Helper', logging.WARNING, f"{root_dir}{os.sep}tt_most_current_{time.strftime('%Y-%m-%d')}.cshd: 4 missing files!"),
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
    assert x_contains_all_y(caplog.record_tuples, [
        ('Checksum_Helper', logging.WARNING, "Found reference beyond the hash file's root dir in file: '%s'. "
                                             "Consider moving/copying the file using ChecksumHelper move/copy "
                                             "to the path that is the most common denominator!"
                                             % os.path.join(root_dir, "sub3", "sub2", "sub3_sub2.sha512")),
        ('Checksum_Helper', logging.WARNING, f'new 3.txt: SHA512 FAILED'),
        ('Checksum_Helper', logging.INFO, f'new 4.txt: SHA512 OK'),
        ('Checksum_Helper', logging.INFO, f'sub1{os.sep}new 2.txt: SHA512 OK'),
        ('Checksum_Helper', logging.INFO, f'sub1{os.sep}new 3.txt: SHA512 OK'),
        ('Checksum_Helper', logging.INFO, f'sub1{os.sep}new 4.txt: SHA512 OK'),
        ('Checksum_Helper', logging.INFO, f'sub1{os.sep}sub2{os.sep}new 2.txt: SHA512 OK'),
        ('Checksum_Helper', logging.INFO, f'sub1{os.sep}sub2{os.sep}new 3.txt: SHA512 OK'),
        ('Checksum_Helper', logging.INFO, f'sub1{os.sep}sub2{os.sep}new 4.txt: SHA512 OK'),
        ('Checksum_Helper', logging.WARNING, f'sub1{os.sep}sub2{os.sep}new 8.txt: MISSING'),
    ])

    assert caplog.record_tuples[10:] == [
        ('Checksum_Helper', logging.WARNING, f"{root_dir}{os.sep}tt_most_current_{time.strftime('%Y-%m-%d')}.cshd: 1 files with wrong CRCs!"),
        ('Checksum_Helper', logging.WARNING, f"{root_dir}{os.sep}tt_most_current_{time.strftime('%Y-%m-%d')}.cshd: 1 missing files!"),
    ]
