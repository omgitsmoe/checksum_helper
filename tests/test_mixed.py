import os
import shutil
import logging
import pytest

from utils import TESTS_DIR, setup_tmpdir_param, read_file, write_file_str

from checksum_helper import split_path, move_fpath, HashFile, gen_hash_from_file


@pytest.mark.parametrize(
        "test_input, expected",
        [
            ("./test/test2/test3.txt", ([".", "test", "test2"], "test3.txt")),
            ("test/test2/test3.txt", (["test", "test2"], "test3.txt")),
            ("./test/test2/", ([".", "test", "test2"], None)),
            ("./test/test2/test3", ([".", "test", "test2"], "test3")),
            ("C:/test/test2/test3.txt", (["C:", "test", "test2"], "test3.txt")),
            ("C:\\test\\test2\\test3.txt", (["C:", "test", "test2"], "test3.txt")),
            (".\\test\\test2\\test3.txt", ([".", "test", "test2"], "test3.txt")),
            (".\\test\\..\\test3.txt", ([".", "test", ".."], "test3.txt")),
            (".\\test\\..\\\\test3.txt", (None, None)),
            ("\\test\\test3.txt", (None, None)),
            ("\\\\test\\test3.txt", (None, None)),
            ("/test\\test3.txt", (None, None)),
        ])
def test_split_path(test_input, expected):
    assert split_path(test_input) == expected


@pytest.mark.parametrize(
        "test_input, expected",
        [
            (("C:\\test\\test2\\test3.txt", "D:\\test4\\test5.txt"),
             "D:\\test4\\test5.txt"),
            (("C:\\test\\test2\\test3.txt", "D:\\test4\\test5"),
             "D:\\test4\\test5"),
            (("C:\\test\\test2\\test3.txt", "D:\\test4\\"),
             "D:\\test4\\test3.txt"),
            (("C:\\test\\test2\\test3.txt", ".\\test4\\test5.txt"),
             "C:\\test\\test2\\test4\\test5.txt"),
            (("C:\\test\\test2\\test3.txt", ".\\..\\test4\\"),
             "C:\\test\\test4\\test3.txt"),
            # trying to go beyond root of drive
            (("C:\\test\\test2\\test3.txt", "..\\..\\..\\"),
             None),
            (("C:\\test\\test2\\test3.txt", ".\\test4\\test5.txt"),
             "C:\\test\\test2\\test4\\test5.txt"),
            # unix path
            (("/test\\test2\\test3.txt", ".\\test4\\test5.txt"),
             None),
            # worng format of src
            (("\\test\\test2\\test3.txt", ".\\test4\\test5.txt"),
             None),
            # unc path
            (("\\\\test\\test2\\test3.txt", ".\\test4\\test5.txt"),
             None),
            # wrong format of mv_path
            (("test\\test2\\test3.txt", ".\\test4\\\\test5.txt"),
             None),
        ])
def test_move_fpath(test_input, expected):
    assert move_fpath(*test_input) == expected


def hf_copyto(srcp, destp):
    h = HashFile(None, srcp)
    # @Hack change cwd so relative paths in hash file can be correctly converted to
    # abspath using os.path.abspath (which uses cwd as starting point)
    os.chdir(os.path.dirname(srcp))
    h.read()
    h.copy_to(destp)
    # @Hack change cwd after copy so relative paths in hash file are valid for verifying
    os.chdir(h.hash_file_dir)
    return h


def test_copyto(setup_tmpdir_param, monkeypatch, caplog):
    tmpdir = setup_tmpdir_param
    root_dir = os.path.join(tmpdir, "tt")
    shutil.copytree(os.path.join(TESTS_DIR, "test_copyto_files", "tt"),
                    os.path.join(root_dir))

    # set input to automatically answer with y so we write the file when asked
    monkeypatch.setattr('builtins.input', lambda x: "y")
    hf = hf_copyto(os.path.join(root_dir, "tt.sha512"), ".\\sub2\\tt_moved.sha512")
    # not reading in the written file only making sure it was written to the correct loc
    assert os.path.isfile(os.path.join(root_dir, "sub2", "tt_moved.sha512"))
    # verifying the paths and hash strings are still correct by directly looping over
    # the filename_hash_dict
    for fpath, hash_str in hf.filename_hash_dict.items():
        assert gen_hash_from_file(fpath, "sha512") == hash_str

    hf = hf_copyto(os.path.join(root_dir, "sub2", "tt_moved.sha512"), "..\\sub1\\sub2\\tt_moved2.sha512")
    # not reading in the written file only making sure it was written to the correct loc
    assert os.path.isfile(os.path.join(root_dir, "sub1", "sub2", "tt_moved2.sha512"))
    # verifying the paths and hash strings are still correct by directly looping over
    # the filename_hash_dict
    for fpath, hash_str in hf.filename_hash_dict.items():
        assert gen_hash_from_file(fpath, "sha512") == hash_str

    hf = hf_copyto(os.path.join(root_dir, "sub1", "sub2", "tt_moved2.sha512"), "..\\.\\tt_moved3.sha512")
    # not reading in the written file only making sure it was written to the correct loc
    assert os.path.isfile(os.path.join(root_dir, "sub1", "tt_moved3.sha512"))
    # verifying the paths and hash strings are still correct by directly looping over
    # the filename_hash_dict
    for fpath, hash_str in hf.filename_hash_dict.items():
        assert gen_hash_from_file(fpath, "sha512") == hash_str

    caplog.set_level(logging.INFO)
    # clear logging records
    caplog.clear()
    # fault mv_path
    hf = hf_copyto(os.path.join(root_dir, "sub1", "tt_moved3.sha512"), "..\\\\tt_moved4.sha512")
    # no file written
    assert not os.path.isfile(os.path.join(root_dir, "sub1", "tt_moved4.sha512"))
    assert caplog.record_tuples == [
        ('Checksum_Helper', logging.WARNING, r'Error: Two following separators in path: ..\\tt_moved4.sha512'),
        ('Checksum_Helper', logging.WARNING, r"Move path '..\\tt_moved4.sha512' was in the wrong format!"),
        ('Checksum_Helper', logging.ERROR, r"Couldn't move file due to a faulty move path!"),

    ]
