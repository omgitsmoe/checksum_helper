import os
import shutil
import logging
import pytest

from utils import TESTS_DIR, setup_tmpdir_param, Args

from checksum_helper import split_path, move_fpath, HashFile, gen_hash_from_file, ChecksumHelper, AbspathDrivesDontMatch, _cl_copy


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


def test_copyto(setup_tmpdir_param, monkeypatch, caplog):
    tmpdir = setup_tmpdir_param
    root_dir = os.path.join(tmpdir, "tt")
    shutil.copytree(os.path.join(TESTS_DIR, "test_copyto_files", "tt"),
                    os.path.join(root_dir))

    # set input to automatically answer with y so we write the file when asked
    monkeypatch.setattr('builtins.input', lambda x: "y")
    a = Args(source_path=os.path.join(root_dir, "tt.sha512"),
             dest_path=".\\sub2\\tt_moved.sha512")
    hf = _cl_copy(a)
    # not reading in the written file only making sure it was written to the correct loc
    assert os.path.isfile(os.path.join(root_dir, "sub2", "tt_moved.sha512"))
    # make sure hash_file_dir and filename were also updated
    assert hf.hash_file_dir == os.path.join(root_dir, "sub2")
    assert hf.filename == "tt_moved.sha512"
    # verifying the paths and hash strings are still correct by directly looping over
    # the filename_hash_dict
    for fpath, hash_str in hf.filename_hash_dict.items():
        assert gen_hash_from_file(fpath, "sha512") == hash_str

    a = Args(source_path=os.path.join(root_dir, "sub2", "tt_moved.sha512"),
             dest_path="..\\sub1\\sub2\\tt_moved2.sha512")
    hf = _cl_copy(a)
    # not reading in the written file only making sure it was written to the correct loc
    assert os.path.isfile(os.path.join(root_dir, "sub1", "sub2", "tt_moved2.sha512"))
    # make sure hash_file_dir and filename were also updated
    assert hf.hash_file_dir == os.path.join(root_dir, "sub1", "sub2")
    assert hf.filename == "tt_moved2.sha512"
    # verifying the paths and hash strings are still correct by directly looping over
    # the filename_hash_dict
    for fpath, hash_str in hf.filename_hash_dict.items():
        assert gen_hash_from_file(fpath, "sha512") == hash_str

    a = Args(source_path=os.path.join(root_dir, "sub1", "sub2", "tt_moved2.sha512"),
             dest_path="..\\.\\tt_moved3.sha512")
    hf = _cl_copy(a)
    # not reading in the written file only making sure it was written to the correct loc
    assert os.path.isfile(os.path.join(root_dir, "sub1", "tt_moved3.sha512"))
    # make sure hash_file_dir and filename were also updated
    assert hf.hash_file_dir == os.path.join(root_dir, "sub1")
    assert hf.filename == "tt_moved3.sha512"
    # verifying the paths and hash strings are still correct by directly looping over
    # the filename_hash_dict
    for fpath, hash_str in hf.filename_hash_dict.items():
        assert gen_hash_from_file(fpath, "sha512") == hash_str

    caplog.set_level(logging.INFO)
    # clear logging records
    caplog.clear()
    # fault mv_path
    a = Args(source_path=os.path.join(root_dir, "sub1", "tt_moved3.sha512"),
             dest_path="..\\\\tt_moved4.sha512")
    hf = _cl_copy(a)
    # no file written
    assert not os.path.isfile(os.path.join(root_dir, "sub1", "tt_moved4.sha512"))
    assert caplog.record_tuples == [
        ('Checksum_Helper', logging.WARNING, r'Error: Two following separators in path: ..\\tt_moved4.sha512'),
        ('Checksum_Helper', logging.WARNING, r"Move path '..\\tt_moved4.sha512' was in the wrong format!"),
        ('Checksum_Helper', logging.ERROR, r"Couldn't move file due to a faulty move path!"),

    ]

def test_warn_abspath(setup_tmpdir_param, monkeypatch, caplog):
    tmpdir = setup_tmpdir_param
    root_dir = os.path.join(tmpdir)

    monkeypatch.setattr('builtins.input', lambda x: "n")
    # we have to generate the warn.sha512 dynamically so we're on the same drive
    dyn_abspath = os.path.abspath(root_dir)
    warn_hf = """f6c5600ed1dbdcfdf829081f5417dccbbd2b9288e0b427e65c8cf67e274b69009cd142475e15304f599f429f260a661b5df4de26746459a3cef7f32006e5d1c1 *new 2.txt
5267768822ee624d48fce15ec5ca79cbd602cb7f4c2157a516556991f22ef8c7b5ef7b18d1ff41c59370efb0858651d44a936c11b7b144c48fe04df3c6a3e8da *{dyn_abspath}\\new 3.txt
e7ef17a6816ef8af636f6d2d4d2707c8ccfda931d0ec2bd576292eafb826d690004798079d4d35249c009b66834ec2d53894915c25bfa8b6cae0db91f4ceb261 *{dyn_abspath}\\new 4.txt""".format(dyn_abspath=dyn_abspath)
    with open(os.path.join(root_dir, "warn.sha512"), "w", encoding="UTF-8-SIG") as w:
        w.write(warn_hf)

    caplog.clear()
    # caplog.set_level sets on root logger by default which is somehow not the logger setup by
    # checksum_helper so specify our logger in the kw param
    caplog.set_level(logging.WARNING, logger='Checksum_Helper')
    checksum_hlpr = ChecksumHelper(root_dir, hash_filename_filter=())
    checksum_hlpr.build_most_current()

    # even if we have 2 abspath in there we only warn once!
    assert caplog.record_tuples == [
        ('Checksum_Helper', logging.WARNING, r'Found absolute path in hash file: {}\warn.sha512'.format(tmpdir)),
    ]

    caplog.clear()
    checksum_hlpr = ChecksumHelper(os.path.join(TESTS_DIR, "test_abspath_warn_files"),
                                   hash_filename_filter=())
    # so we dont accidentally hit a drive that the test is run on try multiple
    drives = "TUVWXYZ"
    excp_msg_expected = "Drive letters of the hash file '{}\\test_abspath_warn_files\\crash.sha512' and the absolute path '{}:\\sub1\\new 2.txt' don't match! This needs to be fixed manually!"
    excp_msgs = [excp_msg_expected.format(TESTS_DIR, d) for d in drives]
    # match=excp_msg makes sure the exception message matches ^^
    with pytest.raises(AbspathDrivesDontMatch) as excp:
        checksum_hlpr.build_most_current()
    # assert we match any exception message with the possible drive letters inserted
    # we can use str(excp) to access the msg but then it starts with the path and the line number
    # or we can use str(excp.value) or excp.value.args[0] then its just the msg but the latter
    # might not include the whole msg?
    assert any([e_msg == str(excp.value) for e_msg in excp_msgs])
    assert caplog.record_tuples == [
        ('Checksum_Helper', logging.WARNING, r'Found absolute path in hash file: {}\crash.sha512'.format(os.path.join(TESTS_DIR, "test_abspath_warn_files"))),
    ]
