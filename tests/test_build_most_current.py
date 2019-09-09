import os
import shutil
import pytest
import time

from utils import TESTS_DIR, setup_tmpdir_param, read_file, write_file_str, Args
from checksum_helper import ChecksumHelper, MixedAlgoHashCollection, _cl_build_most_current


@pytest.fixture
def setup_dir_to_checksum(setup_tmpdir_param):
    tmpdir = setup_tmpdir_param
    root_dir = os.path.join(tmpdir, "tt")
    shutil.copytree(os.path.join(TESTS_DIR, "test_build_most_current_files", "tt"), root_dir)

    return root_dir


@pytest.mark.parametrize("hash_fn_filter,search_depth,filter_deleted,verified_sha_name", [
    ((), 0, False, "most_current.sha512"),
    (("md5",), -1, True, "most_current_md5_filtered.sha512"),
    ((), -1, True, "most_current.sha512"),
    ((), -1, False, "most_current_fd.sha512"),
])
def test_build_most_current(hash_fn_filter, search_depth, filter_deleted, verified_sha_name,
                            setup_dir_to_checksum, monkeypatch):
    monkeypatch.setattr('builtins.input', lambda x: "y")
    root_dir = setup_dir_to_checksum

    a = Args(path=root_dir, hash_filename_filter=hash_fn_filter,
             discover_hash_files_depth=search_depth, filter_deleted=filter_deleted,
             hash_algorithm="sha512")
    _cl_build_most_current(a)

    verified_sha_contents = read_file(os.path.join(TESTS_DIR, "test_build_most_current_files",
                                                   verified_sha_name))
    generated_sha_name = f"{root_dir}\\{os.path.basename(root_dir)}_most_current_{time.strftime('%Y-%m-%d')}.sha512"
    generated_sha_contents = read_file(generated_sha_name)

    assert(verified_sha_contents == generated_sha_contents)
