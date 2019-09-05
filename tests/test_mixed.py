import pytest

from checksum_helper import split_path, move_fpath


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
