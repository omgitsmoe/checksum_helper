import os
import shutil
import pytest
import logging
import time

import checksum_helper

from utils import TESTS_DIR, setup_tmpdir_param, read_file, write_file_str, Args, sort_hf_contents
from checksum_helper.checksum_helper import ChecksumHelper, _cl_move


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
    # move dir that contains a hash file that would've been filtered out by depth limit
    # users can now supply a limited depth and confirm their choice on the cli otherwise
    # we abort so this is a normal test case now
    (os.path.join("sub3"), "sub4", -1, None, "move_sub3_sub4",
     (os.path.join("sub4", "sub3", "file1.txt"), os.path.join("sub4", "sub3", "sub1", "asflkjslekgglkds.jpg"),
      os.path.join("sub4", "sub3", "sub1", "file1.txt"), os.path.join("sub4", "sub3", "sub1", "new 67.txt"),
      os.path.join("sub4", "sub3", "sub1", "tt_sub3_sub1.sha512"), os.path.join("sub4", "sub3", "sub2", "file1.txt"),
      os.path.join("sub4", "sub3", "sub2", "sdgfdfhfgh.jpg"), os.path.join("sub4", "sub3", "sub2", "test2.log"),),
      ((os.path.join("sub4", "sub3", "sub1", "tt_sub3_sub1.sha512"), "tt_sub3_sub1.sha512"),),
    ),
    # move dir will lead to dir to dir overwrite conflict
    (os.path.join("sub3", "sub1"), "sub4", -1, None, ".",
     (os.path.join("sub3", "sub1", "asflkjslekgglkds.jpg"),
      os.path.join("sub3", "sub1", "file1.txt"), os.path.join("sub3", "sub1", "new 67.txt"),
      os.path.join("sub3", "sub1", "tt_sub3_sub1.sha512"),),
      ((os.path.join("sub3", "sub1", "tt_sub3_sub1.sha512"), "tt_sub3_sub1.sha512"),),
    ),
    # move file into dir with overwrite -> error
    (os.path.join("sub4", "file1.txt"), os.path.join("sub2", "sub1"), -1, None, ".",
     (os.path.join("sub2", "sub1", "file1.txt"), os.path.join("sub4", "file1.txt")), (),
    ),
    # try to move to diff drive
    (os.path.join("sub4", "file1.txt"),
     # choose drive dynamically so we're not running the tests on the same drive by chance
     # Windows only!
     os.path.join([d for d in "abcdefghijklmnopqrstuvwxyz" if d != TESTS_DIR[0].lower()][0] + ":", os.sep, "sub2", "sub1"),
     -1, None, ".",
     (os.path.join("sub4", "file1.txt"),), (),
    ),
    # move file to file that already exists
    (os.path.join("sub4", "file1.txt"), os.path.join("sub2", "sub1", "file1.txt"),
     -1, None, ".",
     (os.path.join("sub2", "sub1", "file1.txt"), os.path.join("sub4", "file1.txt")), (),
    ),
    # move dir to path that doesn't exist yet
    (os.path.join("sub3", "sub1"), "sub15", -1, None, "move_sub3_sub1_sub15",
     (os.path.join("sub15", "asflkjslekgglkds.jpg"),
      os.path.join("sub15", "file1.txt"), os.path.join("sub15", "new 67.txt"),
      os.path.join("sub15", "tt_sub3_sub1.sha512"),),
      ((os.path.join("sub15", "tt_sub3_sub1.sha512"), "tt_sub3_sub1.sha512"),),
    ),
    # move dir that doesn't contain a hash file and is covered by hash file in sub3\\sub1
    ("sub1", os.path.join("sub2", "sub222"), -1, None, "move_sub1_sub2_sub222",
     (os.path.join("sub2", "sub222", "desktop.ini"),
      os.path.join("sub2", "sub222", "new 2.txt"), os.path.join("sub2", "sub222", "new 3.txt"),
      os.path.join("sub2", "sub222", "new 4.txt"),
      os.path.join("sub2", "sub222", "sub2", "afsdg.jpg"),
      os.path.join("sub2", "sub222", "sub2", "new 2.txt"),
      os.path.join("sub2", "sub222", "sub2", "new 3.txt"),
      os.path.join("sub2", "sub222", "sub2", "new 4.txt"),
     ), (),
    ),
    # move dir will lead to dir to dir overwrite conflict
    ("sub1", "sub2", -1, None, ".",
     (os.path.join("sub1", "desktop.ini"),
      os.path.join("sub1", "new 2.txt"), os.path.join("sub1", "new 3.txt"),
      os.path.join("sub1", "new 4.txt"),
      os.path.join("sub1", "sub2", "afsdg.jpg"),
      os.path.join("sub1", "sub2", "new 2.txt"),
      os.path.join("sub1", "sub2", "new 3.txt"),
      os.path.join("sub1", "sub2", "new 4.txt"),
     ), (),
    ),
    # move hash file
    (os.path.join("sub3", "sub1", "tt_sub3_sub1.sha512"), "test.sha512", -1, None, "move_sub3_sub1_sha512",
     ("test.sha512",), (("test.sha512", "tt_sub3_sub1.sha512"),),
    ),
    # move dir into itself
    ("sub1", os.path.join("sub1", "sub5"), -1, None, ".",
     (os.path.join("sub1", "desktop.ini"),
      os.path.join("sub1", "new 2.txt"), os.path.join("sub1", "new 3.txt"),
      os.path.join("sub1", "new 4.txt"),
      os.path.join("sub1", "sub2", "afsdg.jpg"),
      os.path.join("sub1", "sub2", "new 2.txt"),
      os.path.join("sub1", "sub2", "new 3.txt"),
      os.path.join("sub1", "sub2", "new 4.txt"),
     ), (),
    ),
])
def test_move_files(src, dst, depth, hash_fn_filter, expected_files_dirname, moved_paths, extra_cmp,
                    setup_dir_to_checksum, caplog):
    root_dir = setup_dir_to_checksum

    # abspath test windows only
    if os.name != 'nt' and os.path.isabs(dst):
        return

    caplog.set_level(logging.WARNING)
    # clear logging records
    caplog.clear()
    a = Args(root_dir=root_dir, hash_filename_filter=hash_fn_filter,
             discover_hash_files_depth=depth, source_path=src, mv_path=dst)
    _cl_move(a)
    if src == os.path.join("sub4", "file1.txt") and dst == os.path.join("sub2", "sub1"):
        # filter out hash file pardir warning
        assert [rt for rt in caplog.record_tuples if not rt[2].startswith("Found reference beyond")] == [
            ('checksum_helper.checksum_helper', logging.ERROR,
             "File %s already exists!"
             % (os.path.join(root_dir, "sub2", "sub1", "file1.txt"),)
            ),
        ]
    elif src == os.path.join("sub4", "file1.txt") and dst == os.path.join("sub2", "sub1", "file1.txt"):
        assert [rt for rt in caplog.record_tuples if not rt[2].startswith("Found reference beyond")] == [
            ('checksum_helper.checksum_helper', logging.ERROR,
             "File %s already exists!" % (os.path.join(root_dir, "sub2", "sub1", "file1.txt"),)
            ),
        ]
    elif src == "sub1" and dst == "sub2":
        assert [rt for rt in caplog.record_tuples if not rt[2].startswith("Found reference beyond")] == [
            ('checksum_helper.checksum_helper', logging.ERROR,
             "Couldn't move file(s): Destination path '%s' already exists"
             % (os.path.join(root_dir, "sub2", "sub1"),)
            ),
        ]
    elif src == "sub1" and dst == os.path.join("sub1", "sub5"):
        assert [rt for rt in caplog.record_tuples if not rt[2].startswith("Found reference beyond")] == [
            ('checksum_helper.checksum_helper', logging.ERROR,
             "Couldn't move file(s): Cannot move a directory '%s' into itself '%s'."
             % (os.path.join(root_dir, "sub1"), os.path.join(root_dir, "sub1", "sub5"))
            ),
        ]
    elif src == os.path.join("sub3", "sub1") and dst == "sub4":
        assert [rt for rt in caplog.record_tuples if not rt[2].startswith("Found reference beyond")] == [
            ('checksum_helper.checksum_helper', logging.ERROR,
             "Couldn't move file(s): Destination path '%s' already exists"
             % (os.path.join(root_dir, "sub4", "sub1"))
            ),
        ]
    elif src == os.path.join("sub4", "file1.txt") and dst == os.path.join([d for d in "abcdefghijklmnopqrstuvwxyz" if d != TESTS_DIR[0].lower()][0] + ":", os.sep, "sub2", "sub1"):
        assert [rt for rt in caplog.record_tuples if not rt[2].startswith("Found reference beyond")] == [
            ('checksum_helper.checksum_helper', logging.ERROR,
             "Can't move files to a different drive than the hash files "
              "that hold their hashes!"),
        ]
    else:
        # only check that src doesnt exist when we shouldn't error
        assert not os.path.exists(src)

    # check that files are at the expected locations
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

@pytest.fixture
def mtime_ordered_hfiles(setup_tmpdir_param):
    tmpdir = setup_tmpdir_param

    hf1 = os.path.join(tmpdir, "1.md5")
    with open(hf1, "w") as f:
        f.write("342452afbc534 *test.txt\n342452afbc534 *test2.txt\n342452afbc534 *test3.txt\n")
    hf1_mtime = os.stat(hf1).st_mtime
    time.sleep(1)

    os.makedirs(os.path.join(tmpdir, "sub"))
    hf2 = os.path.join(tmpdir, "sub", "2.cshd")
    with open(hf2, "w") as f:
        f.write("1234124.5,md5,342452afbc534 test.txt\n1234124.5,md5,342452afbc534 test2.txt\n1234124.5,md5,342452afbc534 test3.txt\n")
    hf2_mtime = os.stat(hf2).st_mtime
    time.sleep(1)

    hf3 = os.path.join(tmpdir, "3.md5")
    with open(hf3, "w") as f:
        f.write("342452afbc534 *test.txt\n342452afbc534 *test2.txt\n342452afbc534 *test3.txt\n")
    hf3_mtime = os.stat(hf3).st_mtime

    return (tmpdir, (hf1, hf2, hf3),
            [(os.path.basename(hf1), hf1_mtime), (os.path.basename(hf2), hf2_mtime),
             (os.path.basename(hf3), hf3_mtime)])

def test_move_preserves_mtime(mtime_ordered_hfiles, monkeypatch):
    root, hfiles, hf_mtimes = mtime_ordered_hfiles

    monkeypatch.setattr(checksum_helper.checksum_helper, "cli_yes_no", lambda x: True)

    src = hfiles[0]
    dst_dir = os.path.join(root, "moved")
    os.makedirs(dst_dir) # so shutil.move moves it inside instead of renaming to "moved"

    a = Args(root_dir=root, hash_filename_filter=None,
             discover_hash_files_depth=1, source_path=src, mv_path=dst_dir)

    _cl_move(a)

    hfiles_after_move = [os.path.join(root, "moved", os.path.basename(hfiles[0])), *hfiles[1:]]
    hf_mtimes_after_move = [(os.path.basename(hf), os.stat(hf).st_mtime) for hf in hfiles_after_move]

    assert hf_mtimes == hf_mtimes_after_move


