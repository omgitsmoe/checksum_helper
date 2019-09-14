import pytest
import os
import shutil
import json
import pickle


TESTS_DIR = os.path.dirname(os.path.realpath(__file__))


def read_file(fn, encoding="UTF-8"):
    with open(fn, "r", encoding=encoding) as f:
        return f.read()


def write_file_str(fn, s):
    with open(fn, "w", encoding="UTF-8") as w:
        w.write(s)


def import_json(fn):
    json_str = read_file(fn)
    return json.loads(json_str)


def export_json(fn, obj):
    json_str = json.dumps(obj, indent=4, sort_keys=True)
    write_file_str(fn, json_str)


def import_pickle(filename):
    with open(filename, 'rb') as f:
        # The protocol version used is detected automatically, so we do not
        # have to specify it.
        obj = pickle.load(f)
    return obj
    

def export_pickle(obj, filename):
    with open(filename, 'wb') as f:
        # Pickle the 'data' dictionary using the highest protocol available.
        pickle.dump(obj, f, pickle.HIGHEST_PROTOCOL)


@pytest.fixture
def setup_tmpdir():
    tmpdir = os.path.join(TESTS_DIR, "tmp")
    # we wont return after yielding if the test raises an exception
    # -> better way to delete at start of next test so we also
    # have the possiblity to check the content of tmpdir manually
    # -> but then we also have to except FileNotFoundError since tmpdir
    # might not exist yet
    try:
        shutil.rmtree(tmpdir)
    except FileNotFoundError:
        pass
    os.makedirs(tmpdir)

    return tmpdir
    # yield tmpdir
    # # del dir and contents after test is done
    # shutil.rmtree(tmpdir)


@pytest.fixture
def setup_tmpdir_param():
    """
    For parametrized pytest fixtures and functions since pytest still accesses
    the tmp directory while switching between params which means we cant delete
    tmpdir -> we try to delete all dirs starting with tmp_ and then we
    create a new tmpdir with name tmp_i where i is the lowest number for which
    tmp_i doesnt exist
    """
    # maybe use @pytest.fixture(autouse=True) -> gets called before and after(with yield)
    # every test

    # we wont return after yielding if the test raises an exception
    # -> better way to delete at start of next test so we also
    # have the possiblity to check the content of tmpdir manually
    # -> but then we also have to except FileNotFoundError since tmpdir
    # might not exist yet
    tmpdir_list = [dirpath for dirpath in os.listdir(TESTS_DIR) if dirpath.startswith(
                   "tmp_") and os.path.isdir(os.path.join(TESTS_DIR, dirpath))]
    for old_tmpdir in tmpdir_list:
        try:
            shutil.rmtree(os.path.join(TESTS_DIR, old_tmpdir))
        except FileNotFoundError:
            pass
        except PermissionError:
            pass

    i = 0
    while True:
        tmpdir = os.path.join(TESTS_DIR, f"tmp_{i}")
        if os.path.isdir(tmpdir):
            i += 1
            continue
        os.makedirs(tmpdir)
        break

    return tmpdir


# stub for testing the _cl funcs directly
class Args:
    def __init__(self, *args, **kwargs):
        self.__dict__.update(kwargs)
