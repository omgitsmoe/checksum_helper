import os
import shutil
import pytest
import time

from utils import TESTS_DIR, setup_tmpdir_param, read_file, write_file_str, Args
from checksum_helper import ChecksumHelper, _cl_move


@pytest.fixture
def setup_dir_to_checksum(setup_tmpdir_param):
    tmpdir = setup_tmpdir_param
    root_dir = os.path.join(tmpdir, "tt")
    shutil.copytree(os.path.join(TESTS_DIR, "test_modify_files", "tt"), root_dir)

    return root_dir


test_modf_dir_abs = os.path.join(TESTS_DIR, "test_modify_files")
HASH_FILES = ("tt.md5", "tt.sha256", "tt.sha512", os.path.join("sub3", "sub1", "tt_sub3_sub1.sha512"))
@pytest.mark.parametrize("src, dst, depth, hash_fn_filter, expected_files_dirname, moved_paths", [
    # cwd when running tests is checksum_helper root dir but relpaths are considered
    # to be relative to the specified root_dir
    (os.path.join("sub3", "sub2", "sdgfdfhfgh.jpg"), "sub2", -1, None, "move_sub3_sub2_jpg",
     (os.path.join("sub2", "sdgfdfhfgh.jpg"),)),
])
def test_move_files(src, dst, depth, hash_fn_filter, expected_files_dirname, moved_paths,
                    setup_dir_to_checksum, monkeypatch):
    root_dir = setup_dir_to_checksum

    a = Args(root_dir=root_dir, hash_filename_filter=hash_fn_filter,
             discover_hash_files_depth=depth, source_path=src, mv_path=dst)
    _cl_move(a)

    # check that files were moved on drive
    assert not os.path.exists(src)
    assert all(os.path.exists(os.path.join(root_dir, p)) for p in moved_paths)

    # check that file paths were moved inside of hash files
    for hf_name in HASH_FILES:
        assert (read_file(os.path.join(root_dir, hf_name), encoding="UTF-8-SIG") ==
                read_file(os.path.join(test_modf_dir_abs, expected_files_dirname,
                                       os.path.basename(hf_name)),
                          encoding="UTF-8-SIG"))
