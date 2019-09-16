import os
import shutil
import pytest
import time

from utils import TESTS_DIR, setup_tmpdir_param, read_file, write_file_str, Args, sort_hf_contents
from checksum_helper import ChecksumHelper, _cl_move


@pytest.fixture
def setup_dir_to_checksum(setup_tmpdir_param):
    tmpdir = setup_tmpdir_param
    root_dir = os.path.join(tmpdir, "tt")
    shutil.copytree(os.path.join(TESTS_DIR, "test_modify_files", "tt"), root_dir)

    return root_dir


test_modf_dir_abs = os.path.join(TESTS_DIR, "test_modify_files")
HASH_FILES = ("tt.md5", "tt.sha256", "tt.sha512", os.path.join("sub3", "sub1", "tt_sub3_sub1.sha512"))
@pytest.mark.parametrize("src, dst, depth, hash_fn_filter, expected_files_dirname, moved_paths, extra_cmp", [
    # cwd when running tests is checksum_helper root dir but relpaths are considered
    # to be relative to the specified root_dir
    (os.path.join("sub3", "sub2", "sdgfdfhfgh.jpg"), "sub2", -1, None, "move_sub3_sub2_jpg",
     (os.path.join("sub2", "sdgfdfhfgh.jpg"),), ()),
    # move hash file which is filtered out by depth or filename_filter settings
    # move dir that contains a hash file but here relative paths HAVE to change
    (os.path.join("sub3"), "sub4", -1, None, "move_sub3_sub4",
     (os.path.join("sub4", "sub3", "file1.txt"), os.path.join("sub4", "sub3", "sub1", "asflkjslekgglkds.jpg"),
      os.path.join("sub4", "sub3", "sub1", "file1.txt"), os.path.join("sub4", "sub3", "sub1", "new 67.txt"),
      os.path.join("sub4", "sub3", "sub1", "tt_sub3_sub1.sha512"), os.path.join("sub4", "sub3", "sub2", "file1.txt"),
      os.path.join("sub4", "sub3", "sub2", "sdgfdfhfgh.jpg"), os.path.join("sub4", "sub3", "sub2", "test2.log"),),
      ((os.path.join("sub4", "sub3", "sub1", "tt_sub3_sub1.sha512"), "tt_sub3_sub1.sha512"),),
    ),
    (os.path.join("sub3", "sub1"), "sub1", -1, None, "move_sub3_sub1_sub1",
     (os.path.join("sub1", "sub1", "asflkjslekgglkds.jpg"),
      os.path.join("sub1", "sub1", "file1.txt"), os.path.join("sub1", "sub1", "new 67.txt"),
      os.path.join("sub1", "sub1", "tt_sub3_sub1.sha512"),),
      ((os.path.join("sub1", "sub1", "tt_sub3_sub1.sha512"), "tt_sub3_sub1.sha512"),),
    ),
    # move dir that contains a hash file that was filtered out by depth of filename_filter settings
    # can use same result hash file dir as op we did before
    (os.path.join("sub3"), "sub4", 1, None, "move_sub3_sub4",
     (os.path.join("sub4", "sub3", "file1.txt"), os.path.join("sub4", "sub3", "sub1", "asflkjslekgglkds.jpg"),
      os.path.join("sub4", "sub3", "sub1", "file1.txt"), os.path.join("sub4", "sub3", "sub1", "new 67.txt"),
      os.path.join("sub4", "sub3", "sub1", "tt_sub3_sub1.sha512"), os.path.join("sub4", "sub3", "sub2", "file1.txt"),
      os.path.join("sub4", "sub3", "sub2", "sdgfdfhfgh.jpg"), os.path.join("sub4", "sub3", "sub2", "test2.log"),),
      ((os.path.join("sub4", "sub3", "sub1", "tt_sub3_sub1.sha512"), "tt_sub3_sub1.sha512"),),
    ),
    # move dir/file with overwrite
    # try to move to diff drive
    # move file to file that already exists
])
def test_move_files(src, dst, depth, hash_fn_filter, expected_files_dirname, moved_paths, extra_cmp,
                    setup_dir_to_checksum, monkeypatch):
    root_dir = setup_dir_to_checksum

    a = Args(root_dir=root_dir, hash_filename_filter=hash_fn_filter,
             discover_hash_files_depth=depth, source_path=src, mv_path=dst)
    _cl_move(a)

    # check that files were moved on drive
    assert not os.path.exists(src)
    assert all([os.path.exists(os.path.join(root_dir, p)) for p in moved_paths])

    # check that file paths were moved inside of hash files
    for hf_name in [hf for hf in HASH_FILES if not hf.startswith(src)]:
        assert (sort_hf_contents(read_file(os.path.join(root_dir, hf_name), encoding="UTF-8-SIG")) ==
                sort_hf_contents(read_file(os.path.join(test_modf_dir_abs, expected_files_dirname,
                                 os.path.basename(hf_name)), encoding="UTF-8-SIG")))
    # additional compares when a hash file was moved
    for hf_current, hf_expected in extra_cmp:
        assert (sort_hf_contents(read_file(os.path.join(root_dir, hf_current), encoding="UTF-8-SIG")) ==
                sort_hf_contents(read_file(os.path.join(test_modf_dir_abs, expected_files_dirname,
                                                        hf_expected), encoding="UTF-8-SIG")))
