import os
import shutil
import pytest
import time

from utils import TESTS_DIR, setup_tmpdir_param, read_file, write_file_str
from checksum_helper import ChecksumHelper


#                       filter, include unchanged
@pytest.fixture(params=(((), False),
                        ((), True),
                        (("md5",), False),
                        (("md5",), True)))
def setup_dir_to_checksum(request, setup_tmpdir_param):
    tmpdir = setup_tmpdir_param
    root_dir = os.path.join(tmpdir, "tt")
    # use "" as last join to make sure tmpdir_failed_md5 ends in os.sep so it gets treated as
    # dir path and not as file path
    # When using copytree, you need to ensure that src exists and dst does not exist.
    # Even if the top level directory contains nothing, copytree won't work because it
    # expects nothing to be at dst and will create the top level directory itself.
    shutil.copytree(os.path.join(TESTS_DIR, "test_incremental_files", "tt"),
                    os.path.join(root_dir, ""))

    filter_str, include_unchanged = request.param
    checksume_hlpr = ChecksumHelper(root_dir, hash_filename_filter=filter_str)
    checksume_hlpr.options["include_unchanged_files_incremental"] = include_unchanged

    yield checksume_hlpr, include_unchanged, root_dir

    del checksume_hlpr


def test_do_incremental(setup_dir_to_checksum, monkeypatch):
    checksume_hlpr, include_unchanged, root_dir = setup_dir_to_checksum
    assert os.path.isabs(checksume_hlpr.root_dir)
    # monkeypatch the "input" function, so that it returns "0,2".
    # This simulates the user entering "y" in the terminal:
    monkeypatch.setattr('builtins.input', lambda x: "y")

    checksume_hlpr.do_incremental_checksums("sha512")

    if include_unchanged:
        verified_sha_name = "tt_2018-04-22_inc_full.sha512"
    else:
        verified_sha_name = "tt_2018-04-22_inc.sha512"
    verified_sha_contents = read_file(os.path.join(TESTS_DIR,
                                                   "test_incremental_files",
                                                   verified_sha_name))

    # find written sha (current date is appended)
    generated_sha_name = f"tt_{time.strftime('%Y-%m-%d')}.sha512"
    generated_sha_contents = read_file(os.path.join(root_dir, generated_sha_name))

    assert(verified_sha_contents == generated_sha_contents)
