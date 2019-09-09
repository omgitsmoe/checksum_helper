import os
import logging
import time

from utils import TESTS_DIR, Args

from checksum_helper import ChecksumHelper, _cl_verify_hfile, _cl_verify_all, _cl_verify_filter


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
    _cl_verify_hfile(a)
    # cwd hasn't changed
    assert starting_cwd == os.getcwd()
    assert caplog.record_tuples == [
        ('Checksum_Helper', logging.INFO, r'..\file1.txt: OK'),
        ('Checksum_Helper', logging.WARNING, r'..\sub1\file1.txt: FAILED'),
        ('Checksum_Helper', logging.INFO, r'file1.txt: OK'),
        ('Checksum_Helper', logging.WARNING, test_verify_root + r'\sub3\sub2\sub3_sub2.sha512: 1 files with wrong CRCs!'),
        ('Checksum_Helper', logging.INFO, test_verify_root + r'\sub3\sub2\sub3_sub2.sha512: No missing files!'),
    ]

    # ------------ all matching, 1 missing ----------
    hfile_path = os.path.join(test_verify_root, "sub1", "sub2", "sub2_1miss.sha512")
    a = Args(hash_file_name=[hfile_path])
    starting_cwd = os.getcwd()

    caplog.clear()
    _cl_verify_hfile(a)
    # cwd hasn't changed
    assert starting_cwd == os.getcwd()
    assert caplog.record_tuples == [
        ('Checksum_Helper', logging.INFO, r'new 2.txt: OK'),
        ('Checksum_Helper', logging.WARNING, r'new 8.txt: MISSING'),
        ('Checksum_Helper', logging.INFO, r'new 4.txt: OK'),
        ('Checksum_Helper', logging.INFO, test_verify_root + r'\sub1\sub2\sub2_1miss.sha512: All files matching their hashes!'),
        ('Checksum_Helper', logging.WARNING, test_verify_root + r'\sub1\sub2\sub2_1miss.sha512: 1 missing files!'),
    ]

    # ----------- no missing all matching ----------
    hfile_path = os.path.join(test_verify_root, "sub1", "sub2", "sub2.sha512")
    a = Args(hash_file_name=[hfile_path])
    starting_cwd = os.getcwd()

    caplog.clear()
    # caplog.set_level sets on root logger by default which is somehow not the logger setup by
    # checksum_helper so specify our logger in the kw param
    _cl_verify_hfile(a)
    # cwd hasn't changed
    assert starting_cwd == os.getcwd()
    assert caplog.record_tuples == [
        ('Checksum_Helper', logging.INFO, r'new 2.txt: OK'),
        ('Checksum_Helper', logging.INFO, r'new 3.txt: OK'),
        ('Checksum_Helper', logging.INFO, r'new 4.txt: OK'),
        ('Checksum_Helper', logging.INFO, test_verify_root + r'\sub1\sub2\sub2.sha512: No missing files and all files matching their hashes'),
    ]

    # ----------- 2 missing 2 crc err ----------
    hfile_path = os.path.join(test_verify_root, "sub1+2_n3+4.sha512")
    a = Args(hash_file_name=[hfile_path])
    starting_cwd = os.getcwd()

    caplog.clear()
    # caplog.set_level sets on root logger by default which is somehow not the logger setup by
    # checksum_helper so specify our logger in the kw param
    _cl_verify_hfile(a)
    # cwd hasn't changed
    assert starting_cwd == os.getcwd()
    assert caplog.record_tuples == [
        ('Checksum_Helper', logging.WARNING, r'new 3.txt: FAILED'),
        ('Checksum_Helper', logging.INFO, r'new 4.txt: OK'),
        ('Checksum_Helper', logging.INFO, r'sub1\new 2.txt: OK'),
        ('Checksum_Helper', logging.INFO, r'sub1\new 3.txt: OK'),
        ('Checksum_Helper', logging.INFO, r'sub1\new 4.txt: OK'),
        ('Checksum_Helper', logging.INFO, r'sub1\sub2\new 2.txt: OK'),
        ('Checksum_Helper', logging.INFO, r'sub1\sub2\new 3.txt: OK'),
        ('Checksum_Helper', logging.WARNING, r'sub1\sub2\new 4.txt: FAILED'),
        ('Checksum_Helper', logging.INFO, r'sub2\sub1\file1.txt: OK'),
        ('Checksum_Helper', logging.WARNING, r'sub5\sub1\file1.txt: MISSING'),
        ('Checksum_Helper', logging.WARNING, r'sub6\file1.txt: MISSING'),
        ('Checksum_Helper', logging.WARNING, test_verify_root + r'\sub1+2_n3+4.sha512: 2 files with wrong CRCs!'),
        ('Checksum_Helper', logging.WARNING, test_verify_root + r'\sub1+2_n3+4.sha512: 2 missing files!'),
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
    _cl_verify_all(a)
    assert caplog.record_tuples == [
        ('Checksum_Helper', logging.INFO, r'new 2.txt: MD5 OK'),
        ('Checksum_Helper', logging.WARNING, r'new 3.txt: SHA512 FAILED'),
        ('Checksum_Helper', logging.INFO, r'new 4.txt: SHA512 OK'),
        ('Checksum_Helper', logging.INFO, r'sub1\new 2.txt: SHA512 OK'),
        ('Checksum_Helper', logging.INFO, r'sub1\new 3.txt: SHA512 OK'),
        ('Checksum_Helper', logging.INFO, r'sub1\new 4.txt: SHA512 OK'),
        ('Checksum_Helper', logging.INFO, r'sub1\sub2\new 2.txt: SHA512 OK'),
        ('Checksum_Helper', logging.INFO, r'sub1\sub2\new 3.txt: SHA512 OK'),
        ('Checksum_Helper', logging.WARNING, r'sub1\sub2\new 4.txt: SHA512 FAILED'),
        ('Checksum_Helper', logging.INFO, r'sub2\sub1\file1.txt: SHA512 OK'),
        ('Checksum_Helper', logging.WARNING, r'sub5\sub1\file1.txt: MISSING'),
        ('Checksum_Helper', logging.WARNING, r'sub6\file1.txt: MISSING'),
        ('Checksum_Helper', logging.WARNING, r'2 files with wrong CRCs!'),
        ('Checksum_Helper', logging.WARNING, r'2 missing files!'),
    ]

    # ------------ all matching, 1 missing, most_current single hash file ----------
    root_dir = os.path.join(test_verify_root, "sub1", "sub2")
    a = Args(root_dir=[root_dir], discover_hash_files_depth=0, hash_filename_filter=())

    caplog.clear()
    _cl_verify_all(a)
    assert caplog.record_tuples == [
        ('Checksum_Helper', logging.INFO, r'new 2.txt: OK'),
        ('Checksum_Helper', logging.INFO, r'new 3.txt: OK'),
        ('Checksum_Helper', logging.INFO, r'new 4.txt: OK'),
        ('Checksum_Helper', logging.WARNING, r'new 8.txt: MISSING'),
        ('Checksum_Helper', logging.INFO, root_dir + '\\' + f'sub2_most_current_{time.strftime("%Y-%m-%d")}.sha512: All files matching their hashes!'),
        ('Checksum_Helper', logging.WARNING, root_dir + '\\' + f'sub2_most_current_{time.strftime("%Y-%m-%d")}.sha512: 1 missing files!'),
    ]

    # ------------ 2 wrong crc, 3 missing, MixedAlgo ----------
    root_dir = test_verify_root
    a = Args(root_dir=[root_dir], discover_hash_files_depth=-1, hash_filename_filter=())

    caplog.clear()
    _cl_verify_all(a)
    assert caplog.record_tuples == [
        ('Checksum_Helper', logging.INFO, r'new 2.txt: MD5 OK'),
        ('Checksum_Helper', logging.INFO, r'sub3\file1.txt: SHA512 OK'),
        ('Checksum_Helper', logging.WARNING, r'sub3\sub1\file1.txt: SHA512 FAILED'),
        ('Checksum_Helper', logging.INFO, r'sub3\sub2\file1.txt: SHA512 OK'),
        ('Checksum_Helper', logging.WARNING, r'new 3.txt: SHA512 FAILED'),
        ('Checksum_Helper', logging.INFO, r'new 4.txt: SHA512 OK'),
        ('Checksum_Helper', logging.INFO, r'sub1\new 2.txt: SHA512 OK'),
        ('Checksum_Helper', logging.INFO, r'sub1\new 3.txt: SHA512 OK'),
        ('Checksum_Helper', logging.INFO, r'sub1\new 4.txt: SHA512 OK'),
        ('Checksum_Helper', logging.INFO, r'sub1\sub2\new 2.txt: SHA512 OK'),
        ('Checksum_Helper', logging.INFO, r'sub1\sub2\new 3.txt: SHA512 OK'),
        ('Checksum_Helper', logging.INFO, r'sub1\sub2\new 4.txt: SHA512 OK'),
        ('Checksum_Helper', logging.INFO, r'sub2\sub1\file1.txt: SHA512 OK'),
        ('Checksum_Helper', logging.WARNING, r'sub5\sub1\file1.txt: MISSING'),
        ('Checksum_Helper', logging.WARNING, r'sub6\file1.txt: MISSING'),
        ('Checksum_Helper', logging.WARNING, r'sub1\sub2\new 8.txt: MISSING'),
        ('Checksum_Helper', logging.WARNING, r'2 files with wrong CRCs!'),
        ('Checksum_Helper', logging.WARNING, r'3 missing files!'),
    ]

    # ------------ 2 wrong crc, 3 missing, HashFile, md5 filtered  ----------
    root_dir = test_verify_root
    # hash_filename_filter literally only filters out the hashfile if a str of
    # hash_filename_filter is in the name of the file without the extension
    a = Args(root_dir=[root_dir], discover_hash_files_depth=-1, hash_filename_filter=("*.md5",))

    caplog.clear()
    _cl_verify_all(a)
    assert caplog.record_tuples == [
        ('Checksum_Helper', logging.INFO, r'sub3\file1.txt: OK'),
        ('Checksum_Helper', logging.WARNING, r'sub3\sub1\file1.txt: FAILED'),
        ('Checksum_Helper', logging.INFO, r'sub3\sub2\file1.txt: OK'),
        ('Checksum_Helper', logging.WARNING, r'new 3.txt: FAILED'),
        ('Checksum_Helper', logging.INFO, r'new 4.txt: OK'),
        ('Checksum_Helper', logging.INFO, r'sub1\new 2.txt: OK'),
        ('Checksum_Helper', logging.INFO, r'sub1\new 3.txt: OK'),
        ('Checksum_Helper', logging.INFO, r'sub1\new 4.txt: OK'),
        ('Checksum_Helper', logging.INFO, r'sub1\sub2\new 2.txt: OK'),
        ('Checksum_Helper', logging.INFO, r'sub1\sub2\new 3.txt: OK'),
        ('Checksum_Helper', logging.INFO, r'sub1\sub2\new 4.txt: OK'),
        ('Checksum_Helper', logging.INFO, r'sub2\sub1\file1.txt: OK'),
        ('Checksum_Helper', logging.WARNING, r'sub5\sub1\file1.txt: MISSING'),
        ('Checksum_Helper', logging.WARNING, r'sub6\file1.txt: MISSING'),
        ('Checksum_Helper', logging.WARNING, r'sub1\sub2\new 8.txt: MISSING'),
        ('Checksum_Helper', logging.WARNING, root_dir + '\\' + f'tt_most_current_{time.strftime("%Y-%m-%d")}.sha512: 2 files with wrong CRCs!'),
        ('Checksum_Helper', logging.WARNING, root_dir + '\\' + f'tt_most_current_{time.strftime("%Y-%m-%d")}.sha512: 3 missing files!'),
    ]


def test_verify_filter(caplog):
    test_verify_root = os.path.join(TESTS_DIR, "test_verify_files", "tt")
    # caplog.set_level sets on root logger by default which is somehow not the logger setup by
    # checksum_helper so specify our logger in the kw param
    caplog.set_level(logging.INFO, logger='Checksum_Helper')
    # ------------ 2 wrong crc, no missing, MixedAlgo ----------
    root_dir = test_verify_root
    a = Args(root_dir=root_dir, discover_hash_files_depth=1, hash_filename_filter=(),
             filter=[
                 r"sub1\*",
                 "new ?.txt",
                    ])

    caplog.clear()
    _cl_verify_filter(a)
    assert caplog.record_tuples == [
        ('Checksum_Helper', logging.INFO, r'new 2.txt: MD5 OK'),
        ('Checksum_Helper', logging.WARNING, r'new 3.txt: SHA512 FAILED'),
        ('Checksum_Helper', logging.INFO, r'new 4.txt: SHA512 OK'),
        ('Checksum_Helper', logging.INFO, r'sub1\new 2.txt: SHA512 OK'),
        ('Checksum_Helper', logging.INFO, r'sub1\new 3.txt: SHA512 OK'),
        ('Checksum_Helper', logging.INFO, r'sub1\new 4.txt: SHA512 OK'),
        ('Checksum_Helper', logging.INFO, r'sub1\sub2\new 2.txt: SHA512 OK'),
        ('Checksum_Helper', logging.INFO, r'sub1\sub2\new 3.txt: SHA512 OK'),
        ('Checksum_Helper', logging.WARNING, r'sub1\sub2\new 4.txt: SHA512 FAILED'),
        ('Checksum_Helper', logging.WARNING, r'2 files with wrong CRCs!'),
        ('Checksum_Helper', logging.INFO, r'No missing files!'),
    ]

    # ------------ 1 crc err, 1 missing, MixedAlgo ----------
    root_dir = test_verify_root
    a = Args(root_dir=root_dir, discover_hash_files_depth=-1, hash_filename_filter=(),
             filter=[
                 r"*file?.txt",
                 r"s*\sub1\**",
                    ])

    caplog.clear()
    _cl_verify_filter(a)
    assert caplog.record_tuples == [
        ('Checksum_Helper', logging.INFO, r'sub3\file1.txt: SHA512 OK'),
        ('Checksum_Helper', logging.WARNING, r'sub3\sub1\file1.txt: SHA512 FAILED'),
        ('Checksum_Helper', logging.INFO, r'sub3\sub2\file1.txt: SHA512 OK'),
        ('Checksum_Helper', logging.INFO, r'sub2\sub1\file1.txt: SHA512 OK'),
        ('Checksum_Helper', logging.WARNING, r'sub5\sub1\file1.txt: MISSING'),
        ('Checksum_Helper', logging.WARNING, r'sub6\file1.txt: MISSING'),
        ('Checksum_Helper', logging.WARNING, r'1 files with wrong CRCs!'),
        ('Checksum_Helper', logging.WARNING, r'2 missing files!'),
    ]

    # ------------ 2 wrong crc, 3 missing, HashFile, md5 filtered  ----------
    root_dir = test_verify_root
    # hash_filename_filter literally only filters out the hashfile if a str of
    # hash_filename_filter is in the name of the file without the extension
    a = Args(root_dir=root_dir, discover_hash_files_depth=-1, hash_filename_filter=("*.md5",),
             filter=[
                 r"",
                 r"sub?\*",
                    ])

    caplog.clear()
    _cl_verify_filter(a)
    assert caplog.record_tuples == [
        ('Checksum_Helper', logging.INFO, r'sub3\file1.txt: OK'),
        ('Checksum_Helper', logging.WARNING, r'sub3\sub1\file1.txt: FAILED'),
        ('Checksum_Helper', logging.INFO, r'sub3\sub2\file1.txt: OK'),
        ('Checksum_Helper', logging.INFO, r'sub1\new 2.txt: OK'),
        ('Checksum_Helper', logging.INFO, r'sub1\new 3.txt: OK'),
        ('Checksum_Helper', logging.INFO, r'sub1\new 4.txt: OK'),
        ('Checksum_Helper', logging.INFO, r'sub1\sub2\new 2.txt: OK'),
        ('Checksum_Helper', logging.INFO, r'sub1\sub2\new 3.txt: OK'),
        ('Checksum_Helper', logging.INFO, r'sub1\sub2\new 4.txt: OK'),
        ('Checksum_Helper', logging.INFO, r'sub2\sub1\file1.txt: OK'),
        ('Checksum_Helper', logging.WARNING, r'sub5\sub1\file1.txt: MISSING'),
        ('Checksum_Helper', logging.WARNING, r'sub6\file1.txt: MISSING'),
        ('Checksum_Helper', logging.WARNING, r'sub1\sub2\new 8.txt: MISSING'),
        ('Checksum_Helper', logging.WARNING, root_dir + '\\' + f'tt_most_current_{time.strftime("%Y-%m-%d")}.sha512: 1 files with wrong CRCs!'),
        ('Checksum_Helper', logging.WARNING, root_dir + '\\' + f'tt_most_current_{time.strftime("%Y-%m-%d")}.sha512: 3 missing files!'),
    ]


    # ------------ 1 wrong crc, 1 missing, HashFile, md5 filtered  ----------
    root_dir = test_verify_root
    # hash_filename_filter literally only filters out the hashfile if a str of
    # hash_filename_filter is in the name of the file without the extension
    a = Args(root_dir=root_dir, discover_hash_files_depth=-1, hash_filename_filter=("*.md5",),
             filter=[
                 r"*new* ?.txt",
                    ])

    caplog.clear()
    _cl_verify_filter(a)
    assert caplog.record_tuples == [
        ('Checksum_Helper', logging.WARNING, r'new 3.txt: FAILED'),
        ('Checksum_Helper', logging.INFO, r'new 4.txt: OK'),
        ('Checksum_Helper', logging.INFO, r'sub1\new 2.txt: OK'),
        ('Checksum_Helper', logging.INFO, r'sub1\new 3.txt: OK'),
        ('Checksum_Helper', logging.INFO, r'sub1\new 4.txt: OK'),
        ('Checksum_Helper', logging.INFO, r'sub1\sub2\new 2.txt: OK'),
        ('Checksum_Helper', logging.INFO, r'sub1\sub2\new 3.txt: OK'),
        ('Checksum_Helper', logging.INFO, r'sub1\sub2\new 4.txt: OK'),
        ('Checksum_Helper', logging.WARNING, r'sub1\sub2\new 8.txt: MISSING'),
        ('Checksum_Helper', logging.WARNING, root_dir + '\\' + f'tt_most_current_{time.strftime("%Y-%m-%d")}.sha512: 1 files with wrong CRCs!'),
        ('Checksum_Helper', logging.WARNING, root_dir + '\\' + f'tt_most_current_{time.strftime("%Y-%m-%d")}.sha512: 1 missing files!'),
    ]
