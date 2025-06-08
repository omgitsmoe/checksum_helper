import os
import shutil
import pytest
import time

from utils import TESTS_DIR, setup_tmpdir_param, read_file, write_file_str, Args
from checksum_helper.checksum_helper import ChecksumHelper, ChecksumHelperData, _cl_build_most_current


@pytest.fixture
def setup_dir_to_checksum(setup_tmpdir_param):
    tmpdir = setup_tmpdir_param
    root_dir = os.path.join(tmpdir, "tt")
    shutil.copytree(os.path.join(TESTS_DIR, "test_build_most_current_files", "tt"), root_dir)

    return root_dir


def test_build_most_current_only_read_unread_files(setup_dir_to_checksum, monkeypatch):
    root_dir = setup_dir_to_checksum
    ch = ChecksumHelper(root_dir)
    ch.discover_hash_files()

    for cshd in ch.all_hash_files:
        if cshd.get_path().endswith("tt2.sha512"):
            continue
        cshd.read()

    read_called_on = []

    def patched_read(s):
        nonlocal read_called_on
        read_called_on.append(s)

    monkeypatch.setattr(
        "checksum_helper.checksum_helper.ChecksumHelperData.read",
        patched_read)

    ch.build_most_current()

    assert len(read_called_on) == 1
    assert read_called_on[0].get_path().endswith("tt2.sha512")


@pytest.mark.parametrize("hash_fn_filter,search_depth,dont_filter_deleted,verified_sha_name", [
    ((), 0, True, "most_current.sha512"),
    (("*.md5",), -1, False, "most_current_md5_filtered.sha512"),
    ((), -1, False, "most_current.sha512"),
    ((), -1, True, "most_current_fd.sha512"),
])
def test_build_most_current_single(hash_fn_filter, search_depth, dont_filter_deleted, verified_sha_name,
                            setup_dir_to_checksum, monkeypatch):
    root_dir = setup_dir_to_checksum

    a = Args(path=root_dir, hash_filename_filter=hash_fn_filter,
             discover_hash_files_depth=search_depth, dont_filter_deleted=dont_filter_deleted,
             hash_algorithm="sha512", out_filename="most_current.sha512")
    _cl_build_most_current(a)

    verified_sha_contents = read_file(os.path.join(TESTS_DIR, "test_build_most_current_files",
                                                   verified_sha_name))
    generated_sha_name = f"{root_dir}{os.sep}most_current.sha512"
    generated_sha_contents = read_file(generated_sha_name)

    assert(verified_sha_contents == generated_sha_contents)


@pytest.mark.parametrize("hash_fn_filter,search_depth,dont_filter_deleted,verified_cshd_name", [
    ((), 0, True, "most_current.cshd"),
    (("*.md5",), -1, False, "most_current_md5_filtered.cshd"),
    ((), -1, False, "most_current.cshd"),
    ((), -1, True, "most_current_fd.cshd"),
])
def test_build_most_current_cshd(hash_fn_filter, search_depth, dont_filter_deleted, verified_cshd_name,
                            setup_dir_to_checksum, monkeypatch):
    root_dir = setup_dir_to_checksum

    shutil.copy2(os.path.join(TESTS_DIR, "test_build_most_current_files", "pre-existing.cshd"),
                 root_dir)

    a = Args(path=root_dir, hash_filename_filter=hash_fn_filter,
             discover_hash_files_depth=search_depth, dont_filter_deleted=dont_filter_deleted,
             hash_algorithm="sha512", out_filename="most_current.cshd")
    _cl_build_most_current(a)

    verified_cshd_contents = read_file(os.path.join(TESTS_DIR, "test_build_most_current_files",
                                                   verified_cshd_name))
    generated_cshd_name = f"{root_dir}{os.sep}most_current.cshd"
    generated_cshd_contents = read_file(generated_cshd_name)

    print("VERIFIED:", verified_cshd_contents.strip())
    print("GEN:", generated_cshd_contents)
    assert(verified_cshd_contents == generated_cshd_contents)


def test_all_paths_normpath():
    root_dir = os.path.join(TESTS_DIR, "test_build_most_current_files", "normalized")

    c = ChecksumHelper(root_dir, hash_filename_filter=None)
    c.options["discover_hash_files_depth"] = -1
    for hf in c.all_hash_files:
        hf.read()
        # make sure all paths are properly normalized so we dont have get sth like this:
        # C://test//abc//123//..//.//file.txt
        assert all(p == os.path.normpath(p) for p in hf.entries.keys())
