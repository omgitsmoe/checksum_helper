import os
import shutil
import pytest
import time

from utils import TESTS_DIR, setup_tmpdir_param, read_file, write_file_str
from checksum_helper import ChecksumHelper, MixedAlgoHashCollection


@pytest.fixture
def setup_dir_to_checksum(setup_tmpdir_param):
    tmpdir = setup_tmpdir_param
    root_dir = os.path.join(tmpdir, "tt")
    shutil.copytree(os.path.join(TESTS_DIR, "test_build_most_current_files", "tt"),
                    os.path.join(root_dir))

    checksum_hlpr = ChecksumHelper(root_dir, hash_filename_filter=())

    return checksum_hlpr, root_dir


@pytest.mark.parametrize("hash_fn_filter,search_depth,filter_deleted,verified_sha_name", [
    ((), 0, False, "most_current.sha512"),
    (("md5",), -1, True, "most_current_md5_filtered.sha512"),
    ((), -1, True, "most_current.sha512"),
    ((), -1, False, "most_current_fd.sha512"),
])
def test_build_most_current(hash_fn_filter, search_depth, filter_deleted, verified_sha_name,
                            setup_dir_to_checksum, monkeypatch):
    monkeypatch.setattr('builtins.input', lambda x: "y")
    checksum_hlpr, root_dir = setup_dir_to_checksum

    checksum_hlpr.options["discover_hash_files_depth"] = search_depth
    checksum_hlpr.hash_filename_filter = hash_fn_filter
    checksum_hlpr.build_most_current()
    if isinstance(checksum_hlpr.hash_file_most_current, MixedAlgoHashCollection):
        checksum_hlpr.hash_file_most_current = checksum_hlpr.hash_file_most_current.to_single_hash_file("sha512")
    if filter_deleted:
        checksum_hlpr.hash_file_most_current.filter_deleted_files()
    checksum_hlpr.hash_file_most_current.write()

    verified_sha_contents = read_file(os.path.join(TESTS_DIR, "test_build_most_current_files",
                                                   verified_sha_name))
    generated_sha_name = f"most_current_{time.strftime('%Y-%m-%d')}.sha512"
    generated_sha_contents = read_file(os.path.join(root_dir, generated_sha_name))

    assert(verified_sha_contents == generated_sha_contents)
