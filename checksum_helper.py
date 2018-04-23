import sys
import os
import time
import hashlib
import logging
import argparse

from logging.handlers import RotatingFileHandler


MODULE_PATH = os.path.dirname(os.path.realpath(__file__))

logger = logging.getLogger("Checksum_Helper")
logger.setLevel(logging.DEBUG)

handler = RotatingFileHandler(
    os.path.join(MODULE_PATH, "chsmhlpr.log"),
    maxBytes=1048576,
    backupCount=5,
    encoding="UTF-8")
handler.setLevel(logging.DEBUG)

# create a logging format
formatter = logging.Formatter(
    "%(asctime)-15s - %(name)-9s - %(levelname)-6s - %(message)s")
# '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
handler.setFormatter(formatter)

# add the handlers to the logger
logger.addHandler(handler)

# create streamhandler
stdohandler = logging.StreamHandler(sys.stdout)
stdohandler.setLevel(logging.INFO)

# create a logging format
formatterstdo = logging.Formatter(
    "%(asctime)s - %(levelname)s - %(message)s", "%H:%M:%S")
stdohandler.setFormatter(formatterstdo)
logger.addHandler(stdohandler)


def cli_yes_no(question_str):
    ans = input(f"{question_str} y/n:\n")
    while True:
        if ans == "n":
            return False
        elif ans == "y":
            return True
        else:
            ans = input(f"\"{ans}\" was not a valid answer, type in \"y\" or \"n\":\n")


def gen_hash_from_file(fname, hash_algo_str, _hex=True):
    # construct a hash object by calling the appropriate constructor function
    hash_obj = hashlib.new(hash_algo_str)
    # open file in read-only byte-mode
    with open(fname, "rb") as f:
        # only read in chunks of size 4096 bytes
        for chunk in iter(lambda: f.read(4096), b""):
            # update it with the data by calling update() on the object
            # as many times as you need to iteratively update the hash
            hash_obj.update(chunk)
    # get digest out of the object by calling digest() (or hexdigest() for hex-encoded string)
    if _hex:
        return hash_obj.hexdigest()
    else:
        return hash_obj.digest()


def build_hashfile_str(*filename_hash_pairs):
    final_str_ln = []
    for hash_fname, hash_str in filename_hash_pairs:
        final_str_ln.append(f"{hash_str} *{hash_fname}")

    return "\n".join(final_str_ln)


# TODO pass hash files directly using cl args
HASH_FILE_EXTENSIONS = ("crc", "md5", "sha", "sha256", "sha512")
# forgot the comma again for single value tuple!!!!!!
DIR_SUBSTR_EXCLUDE = (".git",)


def discover_hash_files(start_path, depth=2, exclude_str_filename=None):
    if exclude_str_filename is None:
        exclude_str_filename = ()

    # os.walk invokes os.path.join to build the 'top' directory name on each iteration; the count
    # of path separators (that is, os.sep) in each directory name is related to its depth. Just
    # substract the starting count to obtain a relative depth.
    # Note that mixing \ and / in the initial directory (both are allowed on Windows) doesn't
    # affect the result, neither using absolute or relative directory names.
    starting_level = start_path.count(os.sep)
    hashfiles = []
    for dirpath, dirnames, fnames in os.walk(start_path):
        current_depth = dirpath.count(os.sep) - starting_level
        if current_depth == depth:
            # dirnames[:] = [] changes list in-place whereas dirnames=[] just reassigsn/rebinds
            # the variable to a new list while the original list (which os.walk is using remains
            # unchanged; also possible to use del but this would break code below
            dirnames[:] = []

        if dirnames:
            # When topdown is true, the caller can modify the dirnames list in-place (e.g., via del
            # or slice assignment), and walk will only recurse into the subdirectories whose names
            # remain in dirnames; this can be used to prune the search...
            dirnames[:] = [d for d in dirnames if not any(ss in d for ss in DIR_SUBSTR_EXCLUDE)]

        for fname in fnames:
            name, ext = fname.rsplit(".", 1)
            if ext in HASH_FILE_EXTENSIONS and all(
                    (s not in name for s in exclude_str_filename)):
                hashfiles.append(os.path.join(dirpath, fname))

    return hashfiles


class ChecksumHelper:
    def __init__(self, root_dir, hash_filename_filter=None):
        self.root_dir = os.path.normpath(root_dir)
        self.root_dir_abs = os.path.abspath(self.root_dir)
        # set working dir to root_dir
        os.chdir(root_dir)
        logger.debug("Set root_dir to %s", self.root_dir_abs)
        self.root_dir_name = os.path.basename(os.path.abspath(self.root_dir))

        self.all_hash_files = []
        # HashFile containing the most current hashes from all the combined hash
        # files that were found using discover_hash_files
        # -> also contains hashes for files that couldve been deleted
        self.hash_file_most_current = None

        # susbtrings that cant be in filename of hash file
        if hash_filename_filter is None:
            self.hash_filename_filter = ()
        elif isinstance(hash_filename_filter, str):
            # ("md5") is NOT a tuple its a string ("md5",) IS a tuple (mind the comma!)
            self.hash_filename_filter = (hash_filename_filter,)
        else:
            self.hash_filename_filter = hash_filename_filter

        # NEVER include "" in hashname filter since: "" in "some_string" is always True
        # (use self.hash_filename_filter here since we might have converted it to a tuple)
        if "" in self.hash_filename_filter:
            logger.warning("Empty string ("") was included in hash_filename_filter "
                           "this means that all hash files will be filtered out!!")

        self.options = {
                "include_unchanged_files_incremental": True,
                "discover_hash_files_depth": 0,
        }

    def discover_hash_files(self):
        hash_files = discover_hash_files(".", depth=self.options["discover_hash_files_depth"],
                                         exclude_str_filename=self.hash_filename_filter)
        self.all_hash_files = [HashFile(self, hfile_path) for hfile_path in hash_files]

    def read_all_hash_files(self):
        if not self.all_hash_files:
            self.discover_hash_files()
        for hash_file in self.all_hash_files:
            hash_file.read()

    def hash_files_initialized(self):
        return True if self.all_hash_files and all(
                hfile.filename_hash_dict for hfile in self.all_hash_files) else False

    def build_most_current(self):
        if not self.hash_files_initialized():
            self.read_all_hash_files()

        used_algos = list(set((hash_file.hash_type for hash_file in self.all_hash_files)))
        self.sort_hash_files_by_mtime()

        if len(used_algos) == 1:
            single_algo = True
            self.hash_file_most_current = HashFile(self, "most_current_"
                                                   f"{time.strftime('%Y-%m-%d')}.{used_algos[0]}")
        else:
            single_algo = False
            self.hash_file_most_current = MixedAlgoHashCollection(self)

        # update dict with dicts from hash files -> sorted
        # dicts with biggest mtime last(newest) -> most current
        for hash_file in self.all_hash_files:
            hash_type = hash_file.hash_type
            for file_path, hash_str in hash_file.filename_hash_dict.items():
                # since we add hashes from different files we have to combine the realtive
                # path IN the hashfile with the path TO the hashfile
                # to get a correct path
                # BUT
                combined_path = os.path.normpath(os.path.join(hash_file.hash_file_dir, file_path))
                # relpath: Return a relative filepath to path either from the current directory or
                # from an optional start directory
                # NOTE(moe): we could either set the cwd to root dir and access everything with
                # this path thats generated here or we could ignore the cwd and always
                # do a join of root_dir and this path
                # doing first -> dont use start=self.root_dir
                combined_path = os.path.relpath(combined_path)
                # NOTE(moe): here we could also check if file_path was an abspath with
                # os.path.isabs then we could just use the abs path
                if single_algo:
                    self.hash_file_most_current.set_hash_for_file(combined_path, hash_str)
                else:
                    self.hash_file_most_current.set_hash_for_file(hash_type, combined_path, hash_str)

    def do_incremental_checksums(self, algo_name):
        """
        Creates checksums for all changed files (that dont match checksums in
        hash_file_most_current)
        """
        if not self.hash_file_most_current:
            self.build_most_current()

        incremental = HashFile(self, f"{self.root_dir_name}_{time.strftime('%Y-%m-%d')}"
                                     f".{algo_name}")

        for dirpath, dirnames, fnames in os.walk("."):
            for fname in fnames:
                file_path = os.path.join(dirpath, fname)
                new_hash, include = self._build_verfiy_hash(file_path, algo_name)
                if include:
                    # NOTE(moe): generating the dict here would be faster instead of using
                    # the set_hash_for_file method but the performance difference is prob
                    # marginal -> premature optimization (for later: remember to normalize
                    # file_path)
                    # filename_hash_dict[os.path.normpath(file_path)] = new_hash
                    incremental.set_hash_for_file(file_path, new_hash)

        incremental.write()

    def _build_verfiy_hash(self, file_path, algo_name):
        new_hash = None
        include = None
        old_hash, hash_algo_str = self.hash_file_most_current.get_hash_by_file_path(
                                  file_path)
        if old_hash is None:
            new_hash = gen_hash_from_file(file_path, algo_name)
            include = True
        else:
            # when building incremental hashfile we have to use
            # the hash type for which we have A HASH in most_current
            # to find out of file changed -> changed -> use new hash type
            new_hash = gen_hash_from_file(file_path, hash_algo_str)
            if new_hash == old_hash:
                logger.debug("Old and new hashes match for file %s!", file_path)
                include = False if not self.options[
                        "include_unchanged_files_incremental"] else True
            else:
                logger.info("File \"%s\" changed, a new hash was generated!", file_path)
                include = True

            if algo_name != hash_algo_str:
                logger.debug("Last hash used a different algorithm -> generating new hash!")
                new_hash = gen_hash_from_file(file_path, algo_name)
                include = True

        return new_hash, include

    def write_most_current(self):
        if not self.hash_file_most_current:
            self.build_most_current()
        self.hash_file_most_current.write()

    def sort_hash_files_by_mtime(self):
        self.all_hash_files = sorted(self.all_hash_files, key=lambda x: x.mtime)


class HashFile:
    def __init__(self, handling_checksumhelper, path_to_hash_file):
        self.handling_checksumhelper = handling_checksumhelper
        # store location of file (or use filename to build loc)
        # so we can build the path to files from root_dir correctly
        # from path in hash file
        self.hash_file_dir, self.filename = os.path.split(path_to_hash_file)
        # i dont thik ill ever need this
        # self.hash_filename_dict = {}
        self.filename_hash_dict = {}
        self.mtime = None
        # path to dir of hash file -> relpath from self.handling_checksumhelper.root_dir
        # since we set cwd to self.handling_checksumhelper.root_dir
        self.hash_type = self.filename.rsplit(".", 1)[-1]

    def get_hash_by_file_path(self, file_path):
        """
        Pass in file_path (normalized here using normpath) to get stored hash for
        that path
        KeyError -> None

        :param file_path: Relative path to file from cwd/self.handling_checksumhelper.root_dir
        :return: Tuple of hash in hex and name of used hash algorithm
        """
        # filename_hash_dict uses normalized paths as keys
        file_path = os.path.normpath(file_path)
        try:
            return self.filename_hash_dict[file_path], self.hash_type
        except KeyError:
            return None, None

    def set_hash_for_file(self, file_path, hash_str):
        """
        Sets hash value in HashFile for specified file_path

        :param file_path: Relative path to file from cwd/self.handling_checksumhelper.root_dir
                          gets normalized here
        :param hash_str:  Hex-string representation of file hash
        """
        self.filename_hash_dict[os.path.normpath(file_path)] = hash_str

    def get_path(self):
        return os.path.join(self.hash_file_dir, self.filename)

    def read(self):
        self.mtime = os.stat(self.get_path()).st_mtime
        # first line had \ufeff which is the BOM for utf-8 with bom
        with open(self.get_path(), "r", encoding="UTF-8") as f:
            # remove BOM (byte order mark) char at beginning of document
            # present if its UTF-8 with BOM
            text = f.read().lstrip(u'\ufeff')

        for ln in text.splitlines():
            try:
                hash_str, file_path = ln.strip().split(" *", 1)
            except ValueError:
                logger.warning("Invalid line in hash file: %s", self.get_path())
                continue
            # use normpath here to ensure that paths get normalized
            # since we use them as keys
            self.filename_hash_dict[os.path.normpath(file_path)] = hash_str

    def write(self):
        if cli_yes_no(f"Do you want to write {self.filename}?"):
            hashfile_str = build_hashfile_str(*self.filename_hash_dict.items())
            # TotalCommander needs UTF-8 BOM for checksum files so use UTF-8-SIG
            with open(self.get_path(), "w", encoding="UTF-8-SIG") as w:
                w.write(hashfile_str)

    def update_from_dict(self, update_dict):
        # TODO(moe): check if dict matches setup of filename_hash_dict
        self.filename_hash_dict.update(update_dict)

    def filter_deleted_files(self):
        self.filename_hash_dict = {fname: hash_str for fname, hash_str
                                   in self.filename_hash_dict.items() if os.path.isfile(
                                       os.path.join(self.hash_file_dir, fname))}


class MixedAlgoHashCollection:
    def __init__(self, handling_checksumhelper):
        self.handling_checksumhelper = handling_checksumhelper
        self.filename_hash_dict = {}

    def set_hash_for_file(self, algo, file_path, hash_str):
        """
        Sets hash value in HashFile for specified file_path

        :param algo: Name string of used hash algorithm
        :param file_path: Relative path to file from cwd/self.handling_checksumhelper.root_dir
                          gets normalized here
        :param hash_str:  Hex-string representation of file hash
        """
        self.filename_hash_dict[os.path.normpath(file_path)] = (hash_str, algo)

    def get_hash_by_file_path(self, file_path):
        """
        Pass in file_path (normalized here using normpath) to get stored hash for
        that path
        KeyError -> None

        :param file_path: Relative path to file from cwd/self.handling_checksumhelper.root_dir
        :return: Tuple of hash in hex and name of used hash algorithm
        """
        # filename_hash_dict uses normalized paths as keys
        file_path = os.path.normpath(file_path)
        try:
            return self.filename_hash_dict[file_path]
        except KeyError:
            return None, None

    def to_single_hash_file(self, convert_algo_name):
        most_current_single = HashFile(self, "most_current_"
                                       f"{time.strftime('%Y-%m-%d')}.{convert_algo_name}")
        # file_path is key and use () to also unpack value which is a 2-tuple
        for file_path, (hash_str, algo_name) in self.filename_hash_dict.items():
            if algo_name != convert_algo_name:
                # verify stored hash using old algo still matches
                new_hash = gen_hash_from_file(file_path, algo_name)
                if new_hash != hash_str:
                    logger.info("File doesnt match most current hash: %s!", hash_str)
                new_hash = gen_hash_from_file(file_path, convert_algo_name)

                most_current_single.set_hash_for_file(file_path, new_hash)
            else:
                most_current_single.set_hash_for_file(file_path, hash_str)

        return most_current_single


def _cl_incremental(args):
    c = ChecksumHelper(args.path,
                       hash_filename_filter=args.hash_filename_filter)
    c.options["include_unchanged_files_incremental"] = False if args.filter_unchanged else True
    c.options["discover_hash_files_depth"] = args.discover_hash_files_depth
    c.do_incremental_checksums(args.hash_algorithm)


def _cl_build_most_current(args):
    c = ChecksumHelper(args.path,
                       hash_filename_filter=args.hash_filename_filter)
    c.options["discover_hash_files_depth"] = args.discover_hash_files_depth
    c.build_most_current()
    if isinstance(c.hash_file_most_current, MixedAlgoHashCollection):
        c.hash_file_most_current = c.hash_file_most_current.to_single_hash_file(args.hash_algorithm)
    if args.filter_deleted:
        c.hash_file_most_current.filter_deleted_files()
    #print(vars(c))
    c.hash_file_most_current.write()


# TODO(moe): test for build_most_current

# checking for change based mtimes -> save in own file format(txt)?
# -> NO since we always want to verify that old files (that shouldnt have changed)
# -> still match their checksums


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Combine discovered checksum files into one with "
                                                 "the most current checksums or build a new "
                                                 "incremental checksum file for the specified dir "
                                                 "and all subdirs")

    subparsers = parser.add_subparsers(title='subcommands', description='valid subcommands',
                                       help='sub-command help', dest="subcmd")  # save name of used subcmd in var

    incremental = subparsers.add_parser("incremental", aliases=["inc"])
    incremental.add_argument("hash_algorithm", type=str)
    incremental.add_argument("path", type=str)
    incremental.add_argument("-fu", "--filter-unchanged", action="store_true",
                             help="Dont include the checksum of unchanged files in the output")
    incremental.add_argument("-d", "--discover-hash-files-depth", default=0, type=int,
                             help="Number of subdirs to descend down to search for hash files; "
                                  "0 -> root dir only, -1 -> max depth")
    # metavar is name used placeholder in help text
    incremental.add_argument("-hf", "--hash-filename-filter", nargs="+", metavar="SUBSTRING",
                             help="Substrings in filenames of hashfiles to exclude from search",
                             type=str)
    # set func to call when subcommand is used
    incremental.set_defaults(func=_cl_incremental)


    build_most_current = subparsers.add_parser("build-most-current", aliases=["build"])
    build_most_current.add_argument("path", type=str)
    build_most_current.add_argument("-alg", "--hash-algorithm", type=str, default="sha512",
                                    help="If most current hashes include mixed algorithms, "
                                         "the specified one will be used to re-do the hash",
                                         choices=("md5", "sha256", "sha512"))
    # store_true -> default false, when specified true <-> store_false reversed
    build_most_current.add_argument("-fd", "--filter-deleted", action="store_false",
                                    help="Dont filter out deleted files in most_current hash file")
    build_most_current.add_argument("-d", "--discover-hash-files-depth", default=3, type=int,
                                    help="Number of subdirs to descend down to search for "
                                    "hash files; 0 -> root dir only, -1 -> max depth")
    # metavar is name used placeholder in help text
    build_most_current.add_argument("-hf", "--hash-filename-filter", nargs="+", 
                                    metavar="SUBSTRING", type=str, help="Substrings in "
                                    "filenames of hashfiles to exclude from search")
    # set func to call when subcommand is used
    build_most_current.set_defaults(func=_cl_build_most_current)

    args = parser.parse_args()
    if len(sys.argv) == 1:
        # default to stdout, but stderr would be better (use sys.stderr, then exit(1))
        parser.print_help()
        sys.exit(0)
    args.func(args)
