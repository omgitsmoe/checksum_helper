import os
import shutil
import pytest
import logging
import time
import binascii
import copy

from typing import cast

from utils import TESTS_DIR, setup_tmpdir_param, read_file, write_file_str, Args
from checksum_helper import ChecksumHelper, _cl_incremental, descend_into, HashedFile, ChecksumHelperData, LOG_LVL_VERBOSE, LOG_LVL_EXTRAVERBOSE


#                       filter, include unchanged
@pytest.fixture(params=(((), False),
                        ((), True),
                        (("md5",), False),
                        (("md5",), True)))
def setup_dir_to_checksum(request, setup_tmpdir_param):
    tmpdir = setup_tmpdir_param
    root_dir = os.path.join(tmpdir, "tt")
    # use "" as last join to make sure tmpdir_failed_md5 ends in os.sep so it gets treated as
    # dir path and not as file path
    # When using copytree, you need to ensure that src exists and dst does not exist.
    # Even if the top level directory contains nothing, copytree won't work because it
    # expects nothing to be at dst and will create the top level directory itself.
    shutil.copytree(os.path.join(TESTS_DIR, "test_incremental_files", "tt"),
                    os.path.join(root_dir, ""))

    filter_str, include_unchanged = request.param
    checksume_hlpr = ChecksumHelper(root_dir, hash_filename_filter=filter_str)
    checksume_hlpr.options["include_unchanged_files_incremental"] = include_unchanged

    yield checksume_hlpr, include_unchanged, root_dir

    del checksume_hlpr


def test_do_incremental(setup_dir_to_checksum):
    checksume_hlpr, include_unchanged, root_dir = setup_dir_to_checksum
    assert os.path.isabs(checksume_hlpr.root_dir)

    checksume_hlpr.do_incremental_checksums("sha512")

    if include_unchanged:
        verified_sha_name = "tt_2018-04-22_inc_full.sha512"
    else:
        verified_sha_name = "tt_2018-04-22_inc.sha512"
    verified_sha_contents = read_file(os.path.join(TESTS_DIR,
                                                   "test_incremental_files",
                                                   verified_sha_name))

    # find written sha (current date is appended)
    generated_sha_name = f"tt_{time.strftime('%Y-%m-%d')}.sha512"
    generated_sha_contents = read_file(os.path.join(root_dir, generated_sha_name))

    assert(verified_sha_contents == generated_sha_contents)


@pytest.mark.parametrize(
        "depth, hash_fn_filter, include_unchanged, whitelist, blacklist, verified_sha_name",
        [
            (-1, None, False, ("err",), ("err",), None),
            (-1, None, False, (), (), "wl_bl.sha512"),
            (1, None, False, (), (), "wl_bl_wo-pre.sha512"),
            # filtered pre existing hash file
            (-1, ("*pre.sha512",), False, (), (), "wl_bl.sha512"),
            # include unchanged
            (-1, None, True, (), (), "wl_bl.sha512"),
            (-1, None, False, (), (), "wl_bl_wo-pre.sha512"),
            # blacklist: no desktop.ini, Thumbs.db or *.log
            (-1, None, True, (), ("desktop.ini", "Thumbs.db", "*.log"),
             "wl_bl_no-desk-log-thumbs_only-txt-jpg.sha512"),
            # whitelist: only txt and jpg
            (-1, None, True, ("*.txt", "*.jpg"), (),
             "wl_bl_no-desk-log-thumbs_only-txt-jpg.sha512"),
            # same without including unchanged or lower depth
            # blacklist: no desktop.ini, Thumbs.db or *.log
            (-1, None, False, (), ("desktop.ini", "Thumbs.db", "*.log"),
             "wl_bl_no-desk-log-thumbs_only-txt-jpg_wo-pre.sha512"),
            # whitelist: only txt and jpg
            (1, None, True, ("*.txt", "*.jpg"), (),
             "wl_bl_no-desk-log-thumbs_only-txt-jpg_wo-pre.sha512"),
            # blacklist: no txt
            (-1, None, False, (), ("*.txt",), "wl_bl_no-txt.sha512"),
            # whitelist: only jpg
            (-1, None, False, ("*.jpg",), (), "wl_bl_only-jpg.sha512"),
            ])
def test_white_black_list(depth, hash_fn_filter, include_unchanged, whitelist, blacklist,
                          verified_sha_name, setup_tmpdir_param, caplog, monkeypatch):
    tmpdir = setup_tmpdir_param
    root_dir = os.path.join(tmpdir, "wl_bl")
    # When using copytree, you need to ensure that src exists and dst does not exist.
    # Even if the top level directory contains nothing, copytree won't work because it
    # expects nothing to be at dst and will create the top level directory itself.
    shutil.copytree(os.path.join(TESTS_DIR, "test_incremental_files", "wl_bl"),
                    os.path.join(root_dir))
    caplog.clear()
    # caplog.set_level sets on root logger by default which is somehow not the logger setup by
    # checksum_helper so specify our logger in the kw param
    caplog.set_level(logging.WARNING, logger='Checksum_Helper')
    monkeypatch.setattr('builtins.input', lambda x: "y")

    a = Args(path=root_dir, hash_filename_filter=hash_fn_filter,
             include_unchanged=include_unchanged, discover_hash_files_depth=depth,
             hash_algorithm="sha512", per_directory=False, whitelist=whitelist, blacklist=blacklist)
    _cl_incremental(a)
    if whitelist is not None and blacklist is not None:
        assert caplog.record_tuples == [
            ('Checksum_Helper', logging.ERROR, 'Can only use either a whitelist or blacklist - not both!'),
            ]
    else:
        verified_sha_contents = read_file(os.path.join(TESTS_DIR,
                                                       "test_incremental_files",
                                                       verified_sha_name))

        # find written sha (current date is appended)
        generated_sha_name = f"wl_bl_{time.strftime('%Y-%m-%d')}.sha512"
        generated_sha_contents = read_file(os.path.join(root_dir, generated_sha_name))

        assert(verified_sha_contents == generated_sha_contents)


@pytest.mark.parametrize(
    "whitelist, blacklist, expected_dir",
    [(None, None, "per_dir_results"),
     (None, [f"sub1{os.sep}*", "*.jpg"], "per_dir_results_bl"),
     ([f"sub1{os.sep}*"], None, "per_dir_results_wl")]
)
def test_do_incremental_per_dir(whitelist, blacklist, expected_dir, setup_tmpdir_param):
    tmpdir = setup_tmpdir_param
    root_dir = os.path.join(tmpdir, "tt")
    shutil.copytree(os.path.join(TESTS_DIR, "test_incremental_files", "per_dir"),
                    os.path.join(root_dir, ""))

    a = Args(path=root_dir, hash_filename_filter=None,
             include_unchanged=True, discover_hash_files_depth=-1,
             hash_algorithm="sha512", per_directory=True, whitelist=whitelist, blacklist=blacklist)
    _cl_incremental(a)

    expected_res = [
        ("root.sha512", f"tt_{time.strftime('%Y-%m-%d')}.sha512"),
        ("sub1.sha512", os.path.join("sub1", f"sub1_{time.strftime('%Y-%m-%d')}.sha512")),
        ("sub2.sha512", os.path.join("sub2", f"sub2_{time.strftime('%Y-%m-%d')}.sha512")),
        ("sub3.sha512", os.path.join("sub3", f"sub3_{time.strftime('%Y-%m-%d')}.sha512")),
        ("sub4.sha512", os.path.join("sub4", f"sub4_{time.strftime('%Y-%m-%d')}.sha512")),
    ]

    for expected_fn, result_fn in expected_res:
        try :
            verified_sha_contents = read_file(os.path.join(TESTS_DIR,
                                                           "test_incremental_files",
                                                           expected_dir,
                                                           expected_fn))
        except FileNotFoundError:
            # make sure generated file is also missing
            assert not os.path.exists(os.path.join(root_dir, result_fn))
            continue

        generated_sha_contents = read_file(os.path.join(root_dir, result_fn))

        assert(verified_sha_contents == generated_sha_contents)


@pytest.mark.parametrize(
    "path, whitelist, blacklist, expected",
    [("foo/", [], [], True),
     ("foo/", ["bar/*"], [], False),
     ("bar/", ["bar/*"], [], True),
     ("bar/", ["bar/*.txt"], [], True),
     ("bar/", ["bar/baz/*.txt"], [], True),
     ("bar/", ["bar/baz/xyz.txt"], [], True),
     ("foo/", ["bar/*", "foo/*"], [], True),
     ("foo/bar/", ["bar/*"], [], False),
     ("foo/bar/", ["bar/*", "foo/*"], [], True),
     ("foo/bar/", ["foo/bar/*"], [], True),
     ("foo/bar/", ["foo/qux/*"], [], False),
     ("foo/", [], ["foo/*"], False),
     ("foo/", [], ["bar/*"], True),
     ("foo/", [], ["bar/*", "foo/*"], False),
     ("foo/", [], ["foo/bar/*"], True),
     ("foo/", [], ["qux/*", "foo/bar/*"], True),
     ("foo/", [], ["foo/bar/xyz.txt"], True),
     ("foo/bar/", [], ["foo/bar/*"], False),
     ("foo/bar/", [], ["foo/*", "foo/bar/*"], False),
     ("foo/bar/", [], ["foo/bar/baz/*.txt"], True),
     ("foo/bar/", [], ["foo/bar/baz/*.txt", "foo/bar/qux/xyz.txt"], True),
     ("foo/bar/", [], ["foo/bar/xyz.txt"], True),
    ])
def test_descend_into(path, whitelist, blacklist, expected):
    assert descend_into(path, whitelist=whitelist, blacklist=blacklist) is expected


build_verify_hf_most_current_data = [
    ("new 2.txt", 1524334794.4067194, "sha512", "f6c5600ed1dbdcfdf829081f5417dccbbd2b9288e0b427e65c8cf67e274b69009cd142475e15304f599f429f260a661b5df4de26746459a3cef7f32006e5d1c1"),
    ("new 3.txt", 1524334698.6291595, "md5", "92eb5ffee6ae2fec3ad71c777531578f"),
    # no hash recorded
    ("new 4.txt", 1524334840.3075361, "sha512", "e7ef17a6816ef8af636f6d2d4d2707c8ccfda931d0ec2bd576292eafb826d690004798079d4d35249c009b66834ec2d53894915c25bfa8b6cae0db91f4ceb261"),
    (f"sub1{os.sep}new 2.txt", 1524334688.5989518, "sha512", "1f40fc92da241694750979ee6cf582f2d5d7d28e18335de05abc54d0560e0f5302860c652bf08d560252aa5e74210546f369fbbbce8c12cfc7957b2652fe9a75"),
    (f"sub1{os.sep}new 3.txt", 1524334859.3268101, "sha512", "0555ffa5af6247333309562cd61d2e1de19a8e1f8927447f78d114098f279eedd387e8c441d1a18f9e5541e750c5176016c379ff5ecb90e16784bd4508477328"),
    (f"sub1{os.sep}new 4.txt", 1524334707.4520152, "sha3_512", "bfe4d7f7377116dc15f794d902621797b72b32396382de2b6e49d4f1d7eabdfddcfc3bc127bb67f92f9458a5733bb21804e7ccd56b4b6f81049339f477cd279d"),
    # no hash recorded
    (f"sub1{os.sep}sub2{os.sep}new 2.txt", 1524334852.8311138, "sha512", "00dbe8c9f126a09af5172b9381c6c7462070aeab0020e49a6c73adbbdd7c14f1230fe4d0e08b81d1631a215a91592a074e625eaaa571e45704f8c5898c2bcca1"),
    (f"sub1{os.sep}sub2{os.sep}new 3.txt", 1524334698.6291595, "md5", "92eb5ffee6ae2fec3ad71c777531578f"),
    (f"sub1{os.sep}sub2{os.sep}new 4.txt", 1524334802.3300772, "sha3_512", "ce24e8e181d24d8189308ada1d6dc8fe780608b865a3e549e8903cebaf5910210487e93d4eb2397e8a0653b64f2e64e8b39298cd29a48effc3c86b96fe43b320"),
]


def test_build_verify(setup_tmpdir_param, caplog) -> None:
    tmpdir = setup_tmpdir_param
    root_dir = os.path.join(cast(str, tmpdir), "tt")
    shutil.copytree(os.path.join(TESTS_DIR, "test_incremental_files", "tt"),
                    os.path.join(root_dir, ""))

    ch = ChecksumHelper(root_dir, None)
    most_current = ChecksumHelperData(ch, os.path.join(root_dir, "tt_most_current.cshd"))
    for i, (rel_fp, mtime, hash_type, hash_str) in enumerate(build_verify_hf_most_current_data):
        if i in (2, 6):
            continue
        abs_fp = os.path.normpath(os.path.join(root_dir, rel_fp))
        most_current.entries[abs_fp] = HashedFile(
                abs_fp, mtime, hash_type, binascii.a2b_hex(hash_str), False)

    ch.hash_file_most_current = most_current

    #
    # no hash recorded -> new with optional collect_fstat
    #

    rel_fp, mtime, hash_type, hash_str = build_verify_hf_most_current_data[2]
    abs_fp = os.path.normpath(os.path.join(root_dir, rel_fp))
    include, generated = ch._build_verfiy_hash(abs_fp, "sha512")
    assert include is True
    assert generated.meta_eql(  # type: ignore
            HashedFile(abs_fp, mtime, "sha512", binascii.a2b_hex(hash_str), False))

    include, generated = ch._build_verfiy_hash(abs_fp, "sha512", collect_fstat=False)
    assert include is True
    assert generated.meta_eql(  # type: ignore
            HashedFile(abs_fp, None, "sha512", binascii.a2b_hex(hash_str), False))

    #
    # hash recorded -> collect_fstat or skip_unchanged where recorded hash mtime -> new should have mtime
    #

    rel_fp, mtime, hash_type, hash_str = build_verify_hf_most_current_data[0]
    abs_fp = os.path.normpath(os.path.join(root_dir, rel_fp))
    include, generated = ch._build_verfiy_hash(abs_fp, "sha512", collect_fstat=False, skip_unchanged=True)
    assert include is ch.options['include_unchanged_files_incremental']
    assert generated.meta_eql(  # type: ignore
            HashedFile(abs_fp, mtime, "sha512", binascii.a2b_hex(hash_str), False))

    # change hash so a new hf gets generated
    bu_hash = most_current.entries[abs_fp].hash_bytes
    most_current.entries[abs_fp].hash_bytes = binascii.a2b_hex(hash_str.replace('0', '2'))
    include, generated = ch._build_verfiy_hash(abs_fp, "sha512", collect_fstat=True)
    assert include is ch.options['include_unchanged_files_incremental']
    assert generated.meta_eql(  # type: ignore
            HashedFile(abs_fp, mtime, "sha512", binascii.a2b_hex(hash_str), False))
    # restore!!
    most_current.entries[abs_fp].hash_bytes = bu_hash

    #
    # hash recorded -> skip_unchanged -> same mtime skip file unless diff hash_type
    #


    caplog.clear()
    caplog.set_level(LOG_LVL_EXTRAVERBOSE, logger='Checksum_Helper')

    ch.options['include_unchanged_files_incremental'] = False
    rel_fp, mtime, hash_type, hash_str = build_verify_hf_most_current_data[3]
    abs_fp = os.path.normpath(os.path.join(root_dir, rel_fp))
    include, generated = ch._build_verfiy_hash(abs_fp, "sha512", skip_unchanged=True)
    assert include is False
    assert generated.meta_eql(  # type: ignore
            HashedFile(abs_fp, mtime, "sha512", binascii.a2b_hex(hash_str), False))

    assert caplog.record_tuples == [
        ('Checksum_Helper', LOG_LVL_EXTRAVERBOSE, f"Skipping generation of a hash for file '{abs_fp}' since the mtime matches!"),
    ]

    # diff hash_type -> should still re-hash

    caplog.clear()

    rel_fp, mtime, hash_type, hash_str = build_verify_hf_most_current_data[3]
    abs_fp = os.path.normpath(os.path.join(root_dir, rel_fp))
    # bu hash since it will get overwritten
    bu_hash = most_current.entries[abs_fp].hash_bytes
    include, generated = ch._build_verfiy_hash(abs_fp, "md5", skip_unchanged=True)
    assert include is True
    assert generated.meta_eql(  # type: ignore
            HashedFile(abs_fp, mtime, "md5", binascii.a2b_hex("0cc175b9c0f1b6a831c399e269772661"), False))

    assert caplog.record_tuples == [
        ('Checksum_Helper', LOG_LVL_EXTRAVERBOSE, f"Skipping generation of a hash for file '{abs_fp}' since the mtime matches!"),
        ('Checksum_Helper', LOG_LVL_VERBOSE, f"Recorded hash used sha512 as algorithm -> re-hashing with md5: {abs_fp}!"),
    ]

    # restore
    ch.options['include_unchanged_files_incremental'] = True
    most_current.entries[abs_fp].hash_bytes = bu_hash

    #
    # hash recorded -> no mtime -> same
    #

    caplog.clear()
    caplog.set_level(LOG_LVL_EXTRAVERBOSE, logger='Checksum_Helper')

    rel_fp, mtime, hash_type, hash_str = build_verify_hf_most_current_data[3]
    abs_fp = os.path.normpath(os.path.join(root_dir, rel_fp))

    # NO mtime
    most_current.entries[abs_fp].mtime = None

    include, generated = ch._build_verfiy_hash(abs_fp, "sha512")
    assert include is ch.options['include_unchanged_files_incremental']
    assert generated.meta_eql(  # type: ignore
            HashedFile(abs_fp, mtime, "sha512", binascii.a2b_hex(hash_str), False))

    assert caplog.record_tuples == [
        ('Checksum_Helper', LOG_LVL_EXTRAVERBOSE, f"Old and new hashes match for file {abs_fp}!"),
    ]

    # restore
    most_current.entries[abs_fp].mtime = mtime

    #
    # hash recorded -> no mtime -> changed
    #

    caplog.clear()

    rel_fp, mtime, hash_type, hash_str = build_verify_hf_most_current_data[3]
    abs_fp = os.path.normpath(os.path.join(root_dir, rel_fp))
    bu_hash = most_current.entries[abs_fp].hash_bytes
    most_current.entries[abs_fp].hash_bytes = binascii.a2b_hex(hash_str.replace('0', '2').replace('a', 'd'))

    # NO mtime
    most_current.entries[abs_fp].mtime = None

    include, generated = ch._build_verfiy_hash(abs_fp, "sha512", collect_fstat=False)
    assert include is True
    assert generated.meta_eql(  # type: ignore
            HashedFile(abs_fp, None, "sha512", binascii.a2b_hex(hash_str), False))

    assert caplog.record_tuples == [
        ('Checksum_Helper', logging.INFO, f"File \"{abs_fp}\" changed, a new hash was generated!"),
    ]

    # restore
    most_current.entries[abs_fp].hash_bytes = bu_hash
    most_current.entries[abs_fp].mtime = mtime

    #
    # hash recorded -> recorded mtime older -> changed
    #

    caplog.clear()

    rel_fp, mtime, hash_type, hash_str = build_verify_hf_most_current_data[3]
    abs_fp = os.path.normpath(os.path.join(root_dir, rel_fp))
    bu_hash = most_current.entries[abs_fp].hash_bytes
    most_current.entries[abs_fp].hash_bytes = binascii.a2b_hex(hash_str.replace('0', '2').replace('a', 'd'))

    # OLDER mtime
    most_current.entries[abs_fp].mtime = mtime - 2

    include, generated = ch._build_verfiy_hash(abs_fp, "sha512")
    assert include is True
    assert generated.meta_eql(  # type: ignore
            HashedFile(abs_fp, mtime, "sha512", binascii.a2b_hex(hash_str), False))

    assert caplog.record_tuples == [
        ('Checksum_Helper', logging.INFO, f"File \"{abs_fp}\" changed, a new hash was generated!"),
    ]

    # restore
    most_current.entries[abs_fp].hash_bytes = bu_hash
    most_current.entries[abs_fp].mtime = mtime

    #
    # hash recorded -> recorded mtime younger -> changed
    #

    caplog.clear()

    rel_fp, mtime, hash_type, hash_str = build_verify_hf_most_current_data[3]
    abs_fp = os.path.normpath(os.path.join(root_dir, rel_fp))
    bu_hash = most_current.entries[abs_fp].hash_bytes
    most_current.entries[abs_fp].hash_bytes = binascii.a2b_hex(hash_str.replace('0', '2').replace('a', 'd'))

    # OLDER mtime
    most_current.entries[abs_fp].mtime = mtime + 2

    include, generated = ch._build_verfiy_hash(abs_fp, "sha512")
    assert include is True
    assert generated.meta_eql(  # type: ignore
            HashedFile(abs_fp, mtime, "sha512", binascii.a2b_hex(hash_str), False))

    assert caplog.record_tuples == [
        ('Checksum_Helper', logging.INFO,
            "File hashes don't match with the file on disk being older "
            "than the recorded modfication time! The hash of the file "
            f"on disk will be used: {abs_fp}")
    ]

    # restore
    most_current.entries[abs_fp].hash_bytes = bu_hash
    most_current.entries[abs_fp].mtime = mtime

    #
    # hash recorded -> recorded mtime same -> changed
    #

    caplog.clear()

    rel_fp, mtime, hash_type, hash_str = build_verify_hf_most_current_data[3]
    abs_fp = os.path.normpath(os.path.join(root_dir, rel_fp))
    bu_hash = most_current.entries[abs_fp].hash_bytes
    most_current.entries[abs_fp].hash_bytes = binascii.a2b_hex(hash_str.replace('0', '2').replace('a', 'd'))

    include, generated = ch._build_verfiy_hash(abs_fp, "sha512")
    assert include is True
    assert generated.meta_eql(  # type: ignore
            HashedFile(abs_fp, mtime, "sha512", binascii.a2b_hex(hash_str), False))

    assert caplog.record_tuples == [
        ('Checksum_Helper', logging.WARNING, f"Unexpected change of file hash, when modification time is the same for file: {abs_fp}"),
    ]

    # restore
    most_current.entries[abs_fp].hash_bytes = bu_hash

    #
    # hash recorded -> diff hash_types -> same + re-hash
    #

    caplog.clear()
    caplog.set_level(LOG_LVL_EXTRAVERBOSE, logger='Checksum_Helper')


    # so normally matching hashes would result in not including the file
    ch.options['include_unchanged_files_incremental'] = False
    rel_fp, mtime, hash_type, hash_str = build_verify_hf_most_current_data[3]
    abs_fp = os.path.normpath(os.path.join(root_dir, rel_fp))

    include, generated = ch._build_verfiy_hash(abs_fp, "md5")
    assert include is True
    assert generated.meta_eql(  # type: ignore
            HashedFile(abs_fp, mtime, "md5", binascii.a2b_hex("0cc175b9c0f1b6a831c399e269772661"), False))

    assert caplog.record_tuples == [
            ('Checksum_Helper', LOG_LVL_EXTRAVERBOSE, f'Old and new hashes match for file {abs_fp}!'),
            ('Checksum_Helper', LOG_LVL_VERBOSE, f"Recorded hash used sha512 as algorithm -> re-hashing with md5: {abs_fp}!")
    ]

    # restore
    ch.options['include_unchanged_files_incremental'] = True

    #
    # permission/file not found
    #

    include, generated = ch._build_verfiy_hash(os.path.join(root_dir, "fsadfasdf sadfs.txt"), "sha512")
    assert include is False
    assert generated is None

