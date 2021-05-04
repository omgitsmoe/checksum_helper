import os
import shutil
import pytest
import logging
import time

from utils import TESTS_DIR, setup_tmpdir_param, read_file, write_file_str, Args
from checksum_helper import ChecksumHelper, _cl_incremental


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


def test_do_incremental_per_dir(setup_tmpdir_param):
    tmpdir = setup_tmpdir_param
    root_dir = os.path.join(tmpdir, "tt")
    shutil.copytree(os.path.join(TESTS_DIR, "test_incremental_files", "per_dir"),
                    os.path.join(root_dir, ""))

    a = Args(path=root_dir, hash_filename_filter=None,
             include_unchanged=True, discover_hash_files_depth=-1,
             hash_algorithm="sha512", per_directory=True, whitelist=None, blacklist=None)
    _cl_incremental(a)

    expected_res = [
        ("root.sha512", f"tt_{time.strftime('%Y-%m-%d')}.sha512"),
        ("sub1.sha512", os.path.join("sub1", f"sub1_{time.strftime('%Y-%m-%d')}.sha512")),
        ("sub2.sha512", os.path.join("sub2", f"sub2_{time.strftime('%Y-%m-%d')}.sha512")),
        ("sub3.sha512", os.path.join("sub3", f"sub3_{time.strftime('%Y-%m-%d')}.sha512")),
        ("sub4.sha512", os.path.join("sub4", f"sub4_{time.strftime('%Y-%m-%d')}.sha512")),
    ]

    for expected_fn, result_fn in expected_res:
        verified_sha_contents = read_file(os.path.join(TESTS_DIR,
                                                       "test_incremental_files",
                                                       "per_dir_results",
                                                       expected_fn))

        generated_sha_contents = read_file(os.path.join(root_dir, result_fn))

        assert(verified_sha_contents == generated_sha_contents)
