import os
import shutil
import logging
import time
import pytest

from utils import TESTS_DIR, setup_tmpdir_param, Args

from checksum_helper import split_path, move_fpath, HashedFile, gen_hash_from_file, ChecksumHelper, _cl_copy_hash_file, discover_hash_files, ChecksumHelperData


def test_copyto(setup_tmpdir_param, monkeypatch, caplog) -> None:
    tmpdir = setup_tmpdir_param
    root_dir = os.path.join(tmpdir, "tt")
    shutil.copytree(os.path.join(TESTS_DIR, "test_copyto_files", "tt"),
                    os.path.join(root_dir))

    with open(os.path.join(TESTS_DIR, "test_copyto_files", "tt", "tt.sha512"), 'r', encoding='utf-8-sig') as f:
        orig = f.read().replace("\\", os.sep)

    # set input to automatically answer with y so we write the file when asked
    monkeypatch.setattr('builtins.input', lambda x: "y")
    f1 = os.path.join(root_dir, "tt.sha512")
    a = Args(source_path=f1,
             dest_path=f".{os.sep}sub2{os.sep}tt_moved.sha512")
    hf = _cl_copy_hash_file(a)
    f1_moved = os.path.join(root_dir, "sub2", "tt_moved.sha512")
    assert os.path.isfile(f1_moved)
    # preserved mtime
    assert os.stat(f1).st_mtime == os.stat(f1_moved).st_mtime

    with open(os.path.join(root_dir, "sub2", "tt_moved.sha512"), 'r', encoding='utf-8-sig') as f:
        moved = f.read()
    expected = orig.replace("*n", f"*../n").replace(
            f"*sub2/", "*").replace("*sub1", f"*../sub1")
    assert expected == moved

    f2 = f1_moved
    a = Args(source_path=f2,
             dest_path=f"..{os.sep}sub1{os.sep}sub2{os.sep}tt_moved2.sha512")
    hf = _cl_copy_hash_file(a)
    f2_moved = os.path.join(root_dir, "sub1", "sub2", "tt_moved2.sha512")
    assert os.path.isfile(f2_moved)

    with open(os.path.join(root_dir, "sub1", "sub2", "tt_moved2.sha512"), 'r', encoding='utf-8-sig') as f:
        moved = f.read()
    expected = orig.replace("*n", f"*../../n").replace(f"*sub2/", f"*../../sub2/").replace(
            f"*sub1/sub2/", "*").replace(f"*sub1/", f"*../")
    assert expected == moved
    # preserved mtime
    assert os.stat(f2).st_mtime == os.stat(f2_moved).st_mtime

    a = Args(source_path=os.path.join(root_dir, "sub1", "sub2", "tt_moved2.sha512"),
             dest_path=f"..{os.sep}.{os.sep}tt_moved3.sha512")
    hf = _cl_copy_hash_file(a)
    # not reading in the written file only making sure it was written to the correct loc
    assert os.path.isfile(os.path.join(root_dir, "sub1", "tt_moved3.sha512"))


def test_warn_abspath(setup_tmpdir_param, monkeypatch, caplog):
    tmpdir = setup_tmpdir_param
    root_dir = os.path.join(tmpdir)

    monkeypatch.setattr('builtins.input', lambda x: "n")
    # we have to generate the warn.sha512 dynamically so we're on the same drive
    dyn_abspath = os.path.abspath(root_dir)
    warn_hf = f"""f6c5600ed1dbdcfdf829081f5417dccbbd2b9288e0b427e65c8cf67e274b69009cd142475e15304f599f429f260a661b5df4de26746459a3cef7f32006e5d1c1 *new 2.txt
5267768822ee624d48fce15ec5ca79cbd602cb7f4c2157a516556991f22ef8c7b5ef7b18d1ff41c59370efb0858651d44a936c11b7b144c48fe04df3c6a3e8da *{dyn_abspath}{os.sep}new 3.txt
e7ef17a6816ef8af636f6d2d4d2707c8ccfda931d0ec2bd576292eafb826d690004798079d4d35249c009b66834ec2d53894915c25bfa8b6cae0db91f4ceb261 *{dyn_abspath}{os.sep}new 4.txt""".format(dyn_abspath=dyn_abspath)
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
        ('Checksum_Helper', logging.WARNING,
         f'Read failed! Found absolute path in hash file: {tmpdir}{os.sep}warn.sha512'),
    ]


@pytest.mark.parametrize(
        "depth, exclude, expected",
        [
            (-1, None, (
                f"HDDCol_2019-07-12.sha256",
                f"infodump_2019-04-06.sha512",
                f"picsonly-2016-08-23.md5",
                f"sub1{os.sep}Important Backups-2016-08-21.sha512",
                f"sub1{os.sep}Important Backups-2017-12-18.md5",
                f"sub1{os.sep}Important Backups-2018-07-02.sha512",
                f"sub1{os.sep}sub2{os.sep}backup_2019-07-20.sha512",
                f"sub1{os.sep}sub2{os.sep}backup_most_current_2019-07-19.sha512",
                f"sub1{os.sep}sub2{os.sep}backup-add-2019-07-20.sha256",
                f"sub2{os.sep}catalog-2016-05-04.sha512",
                f"sub2{os.sep}catalog-2017-10-28.sha512",
                f"sub2{os.sep}sub1{os.sep}picsonly-2015-11-18.sha512",
                f"sub2{os.sep}sub1{os.sep}picsonly-2016-05-04.sha512",
                f"sub3{os.sep}Important Backups-2016-07-09.sha512",
                f"sub3{os.sep}Important Backups-2017-07-24.sha512",
                f"sub3{os.sep}Important Backups-2018-03-11.sha512",
                f"sub3{os.sep}sub1{os.sep}ebook-2016-jan.sha512",
                f"sub3{os.sep}sub2{os.sep}ebook-2016-05.sha512",
                f"sub3{os.sep}sub2{os.sep}ebooks-2017-12.md5",
                # f"sub4{os.sep}em-v2bgufjgpki0315.crc",
                f"sub4{os.sep}sub1{os.sep}backup-moved-2019-07-19.sha512",
                f"thumbs.sha512",
                )
        ),
            (0, None, (
                f"HDDCol_2019-07-12.sha256",
                f"infodump_2019-04-06.sha512",
                f"picsonly-2016-08-23.md5",
                f"thumbs.sha512",
                )
        ),
            (1, None, (
                f"HDDCol_2019-07-12.sha256",
                f"infodump_2019-04-06.sha512",
                f"picsonly-2016-08-23.md5",
                f"sub1{os.sep}Important Backups-2016-08-21.sha512",
                f"sub1{os.sep}Important Backups-2017-12-18.md5",
                f"sub1{os.sep}Important Backups-2018-07-02.sha512",
                f"sub2{os.sep}catalog-2016-05-04.sha512",
                f"sub2{os.sep}catalog-2017-10-28.sha512",
                f"sub3{os.sep}Important Backups-2016-07-09.sha512",
                f"sub3{os.sep}Important Backups-2017-07-24.sha512",
                f"sub3{os.sep}Important Backups-2018-03-11.sha512",
                # f"sub4{os.sep}em-v2bgufjgpki0315.crc",
                f"thumbs.sha512",
                )
        ),
            (-1, ("*2016*",), (
                f"HDDCol_2019-07-12.sha256",
                f"infodump_2019-04-06.sha512",
                f"sub1{os.sep}Important Backups-2017-12-18.md5",
                f"sub1{os.sep}Important Backups-2018-07-02.sha512",
                f"sub1{os.sep}sub2{os.sep}backup_2019-07-20.sha512",
                f"sub1{os.sep}sub2{os.sep}backup_most_current_2019-07-19.sha512",
                f"sub1{os.sep}sub2{os.sep}backup-add-2019-07-20.sha256",
                f"sub2{os.sep}catalog-2017-10-28.sha512",
                f"sub2{os.sep}sub1{os.sep}picsonly-2015-11-18.sha512",
                f"sub3{os.sep}Important Backups-2017-07-24.sha512",
                f"sub3{os.sep}Important Backups-2018-03-11.sha512",
                f"sub3{os.sep}sub2{os.sep}ebooks-2017-12.md5",
                # f"sub4{os.sep}em-v2bgufjgpki0315.crc",
                f"sub4{os.sep}sub1{os.sep}backup-moved-2019-07-19.sha512",
                f"thumbs.sha512",
                )
        ),
            (-1, ("*.sha256", "*?ackup*"), (
                f"infodump_2019-04-06.sha512",
                f"picsonly-2016-08-23.md5",
                f"sub2{os.sep}catalog-2016-05-04.sha512",
                f"sub2{os.sep}catalog-2017-10-28.sha512",
                f"sub2{os.sep}sub1{os.sep}picsonly-2015-11-18.sha512",
                f"sub2{os.sep}sub1{os.sep}picsonly-2016-05-04.sha512",
                f"sub3{os.sep}sub1{os.sep}ebook-2016-jan.sha512",
                f"sub3{os.sep}sub2{os.sep}ebook-2016-05.sha512",
                f"sub3{os.sep}sub2{os.sep}ebooks-2017-12.md5",
                # f"sub4{os.sep}em-v2bgufjgpki0315.crc",
                f"thumbs.sha512",
                )
        ),
            (-1, (f"sub1{os.sep}*", "thumbs.sha512"), (
                f"HDDCol_2019-07-12.sha256",
                f"infodump_2019-04-06.sha512",
                f"picsonly-2016-08-23.md5",
                f"sub2{os.sep}catalog-2016-05-04.sha512",
                f"sub2{os.sep}catalog-2017-10-28.sha512",
                f"sub2{os.sep}sub1{os.sep}picsonly-2015-11-18.sha512",
                f"sub2{os.sep}sub1{os.sep}picsonly-2016-05-04.sha512",
                f"sub3{os.sep}Important Backups-2016-07-09.sha512",
                f"sub3{os.sep}Important Backups-2017-07-24.sha512",
                f"sub3{os.sep}Important Backups-2018-03-11.sha512",
                f"sub3{os.sep}sub1{os.sep}ebook-2016-jan.sha512",
                f"sub3{os.sep}sub2{os.sep}ebook-2016-05.sha512",
                f"sub3{os.sep}sub2{os.sep}ebooks-2017-12.md5",
                # f"sub4{os.sep}em-v2bgufjgpki0315.crc",
                f"sub4{os.sep}sub1{os.sep}backup-moved-2019-07-19.sha512",
                )
        ),
        ]
    )
def test_discover_hashfiles(depth, exclude, expected):
    root_dir = os.path.join(TESTS_DIR, "test_mixed_files", "discover")
    assert sorted(discover_hash_files(root_dir, depth, exclude_pattern=exclude)) == sorted([
            os.path.join(root_dir, p.replace('\\', os.sep)) for p in expected])


def test_warn_pardir(caplog):
    root_dir = os.path.join(TESTS_DIR, "test_mixed_files", "warn_pardir")
    caplog.clear()
    caplog.set_level(logging.WARNING, logger='Checksum_Helper')
    hf = ChecksumHelperData(None, os.path.join(root_dir, "ok.sha512"))
    hf.read()
    assert caplog.record_tuples == []

    caplog.clear()
    hf = ChecksumHelperData(None, os.path.join(root_dir, "warn.sha512"))
    hf.read()
    assert caplog.record_tuples == [
        ('Checksum_Helper', logging.WARNING, "Found reference beyond the hash file's root dir in file: '%s'. "
                                             "Consider moving/copying the file using ChecksumHelper move/copy "
                                             "to the path that is the most common denominator!"
                                             % os.path.join(root_dir, "warn.sha512")),
    ]


def test_write_updates_mtime(setup_tmpdir_param, monkeypatch):
    tmpdir = setup_tmpdir_param

    fn = os.path.join(tmpdir, "test.cshd")
    hf = ChecksumHelperData(ChecksumHelper(tmpdir), fn)
    hashed = HashedFile(filename = os.path.join(tmpdir, "test.txt"), mtime = None, hash_type = "md5",
                        hash_bytes = b"342432", text_mode = False)
    hf.set_entry(hashed.filename, hashed)
    hf.write()

    assert hf.mtime is not None
    old = hf.mtime

    time.sleep(1)
    hf.write(force=True)
    assert hf.mtime > old


@pytest.mark.parametrize(
        "preserve", [True, False])
def test_preserve_mtime(preserve, setup_tmpdir_param):
    tmpdir = setup_tmpdir_param

    fn = os.path.join(tmpdir, "test.cshd")
    hf = ChecksumHelperData(ChecksumHelper(tmpdir), fn)
    hashed = HashedFile(filename = os.path.join(tmpdir, "test.txt"), mtime = None, hash_type = "md5",
                        hash_bytes = b"342432", text_mode = False)
    hf.set_entry(hashed.filename, hashed)
    hf.write()
    orig_mtime = os.stat(fn).st_mtime

    time.sleep(1)
    hf.write(force = True, preserve_mtime = preserve)
    if preserve:
        assert os.stat(fn).st_mtime == orig_mtime
    else:
        assert os.stat(fn).st_mtime > orig_mtime


