import sys
import os
import shutil
import time
import hashlib
import logging
import argparse

from logging.handlers import RotatingFileHandler


MODULE_PATH = os.path.dirname(os.path.realpath(__file__))
LOG_BASENAME = "chsmhlpr.log"

logger = logging.getLogger("Checksum_Helper")
logger.setLevel(logging.DEBUG)

handler = RotatingFileHandler(
    os.path.join(MODULE_PATH, LOG_BASENAME),
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


def wildcard_match(pattern, text):
    """
    Adapted and fixed version from: https://www.tutorialspoint.com/Wildcard-Pattern-Matching
    Original by Samual Sam
    Wildcards:
    '?' matches any one character
    '*' matches any sequence of zero or more characters
    """
    n = len(text)
    m = len(pattern)

    # empty pattern
    if m == 0:
        return n == 0

    i, j = 0, 0
    text_ptr, pattern_ptr = -1, -1
    while i < n:
        # as ? used for one character
        if j < m and pattern[j] == '?':
            i += 1
            j += 1
        # as * used for one or more character
        elif j < m and pattern[j] == '*':
            text_ptr = i
            pattern_ptr = j
            j += 1
        # matching text and pattern characters
        elif j < m and text[i] == pattern[j]:
            i += 1
            j += 1
        # pattern_ptr is already updated
        elif pattern_ptr != -1:
            j = pattern_ptr + 1
            i = text_ptr + 1
            text_ptr += 1
        else:
            return False

    # move along left over * in pattern since they can represent empty string
    while j < m and pattern[j] == '*':
        j += 1  # j will increase when wildcard is *

    # check whether pattern is finished or not
    if j == m:
        return True
    return False


def split_path(path_str):
    result = []
    sep = ('/', '\\')
    if path_str[0] == '/':
        logger.error("Absolute UNIX paths not supported!")
        return None, None
    elif path_str.startswith('\\\\'):
        logger.error("UNC paths not supported!")
        return None, None
    elif path_str[0] == '\\':
        logger.error("Path '%s' is wrongly formatted!", path_str)
        return None, None

    curr = ""
    for c in path_str:
        if c in sep:
            if not curr:
                # two seps in a row
                logger.warning("Error: Two following separators in path: %s", path_str)
                return None, None
            result.append(curr)
            curr = ""
        else:
            curr += c
    # path ending in sep -> dont append empty string
    filename = None
    if path_str[-1] not in sep:  # ending in sep -> file path
        filename = curr
    return result, filename


def move_fpath(abspath, mv_path):
    """
    C:\\test1\\test2\\test.txt, ..\\test3\\ -> C:\\test1\\test3\\test.txt
    C:\\test1\\test2\\test.txt, ..\\test3\\test_mv.txt -> C:\\test1\\test3\\test_mv.txt
    Assumes mv_path ending in a separator(/ or \\) is a folder the file should be moved to
    otherwise the path is assumed to be a file path
    e.g. ./test/test2.txt -> file path, ./test/test2 or ./test/test2/ -> dir path
    :param abspath: Absolute path to the file
    :param mv_path: Absolute or relative path
    """
    # if its a file head is the dir and tail the file name
    # if its a dir tail will be empty ONLY if path ends in / or \
    head, tail = os.path.split(abspath)
    mv_path_split, mv_filename = split_path(mv_path)
    if mv_path_split is None:
        logger.warning("Move path '%s' was in the wrong format!", mv_path)
        return None
    if os.path.isabs(mv_path):
        if mv_filename is None:
            return os.path.join(mv_path, tail)
        return mv_path
    else:
        curr_path, fname = split_path(abspath)
        if curr_path is None:
            logger.warning("Source path '%s' was in the wrong format!", abspath)
            return None

        for cd in mv_path_split:
            if cd == "..":
                if len(curr_path) > 1:
                    curr_path.pop()
                else:
                    logger.warning("Tried to go beyond root of drive!")
                    return None
            elif cd == ".":
                continue
            else:
                curr_path.append(cd)
        if mv_filename is None:
            curr_path.append(tail)
        else:
            curr_path.append(mv_filename)
        return os.sep.join(curr_path)


def gen_hash_from_file(fname, hash_algo_str, _hex=True):
    # construct a hash object by calling the appropriate constructor function
    hash_obj = hashlib.new(hash_algo_str)
    try:
        # open file in read-only byte-mode
        with open(fname, "rb") as f:
            # only read in chunks of size 4096 bytes
            for chunk in iter(lambda: f.read(4096), b""):
                # update it with the data by calling update() on the object
                # as many times as you need to iteratively update the hash
                hash_obj.update(chunk)
    except FileNotFoundError:
        logger.debug("Couldn't open file %s for hashing!", fname)
        return None
    # get digest out of the object by calling digest() (or hexdigest() for hex-encoded string)
    if _hex:
        return hash_obj.hexdigest()
    else:
        return hash_obj.digest()


def build_hashfile_str(*filename_hash_pairs):
    final_str_ln = []
    for hash_fname, hash_str in filename_hash_pairs:
        final_str_ln.append(f"{hash_str} *{hash_fname}")

    # end in newline since POSIX defines a line as: A sequence of zero or more
    # non- <newline> characters plus a terminating <newline> character
    return "\n".join(final_str_ln) + '\n'


HASH_FILE_EXTENSIONS = ("crc", "md5", "sha", "sha256", "sha512")
# forgot the comma again for single value tuple!!!!!!
# dirs starting with a substring in the tuple below will not be searched for hash files
DIR_START_STR_EXCLUDE = (".git",)


def discover_hash_files(start_path, depth=2, exclude_pattern=None):
    if exclude_pattern is None:
        exclude_pattern = ()

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
            dirnames[:] = [d for d in dirnames if not any(d.startswith(s)
                           for s in DIR_START_STR_EXCLUDE)]

        for fname in fnames:
            try:
                name, ext = fname.rsplit(".", 1)
                rel_fp = os.path.join(dirpath, fname).replace(start_path + os.sep, '', 1)
            except ValueError:
                # no file extentsion
                continue
            # no exclude patterns -> append files with supported hash file extensions
            # exclude patterns -> supported extension and not matching any of the exclude patterns
            if ((not exclude_pattern and (ext in HASH_FILE_EXTENSIONS)) or 
                    (ext in HASH_FILE_EXTENSIONS and not any(
                        wildcard_match(pat, rel_fp) for pat in exclude_pattern))):
                hashfiles.append(os.path.join(dirpath, fname))

    return hashfiles


class ChecksumHelper:
    def __init__(self, root_dir, hash_filename_filter=None):
        self.root_dir = os.path.abspath(os.path.normpath(root_dir))
        self.root_dir_name = os.path.basename(self.root_dir)

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

        self.options = {
            "include_unchanged_files_incremental": True,
            "discover_hash_files_depth": -1,
            "filename_filter": ["!*.log"],
            "directory_filter": ["!__pycache__"],
        }

    def discover_hash_files(self):
        hash_files = discover_hash_files(self.root_dir,
                                         depth=self.options["discover_hash_files_depth"],
                                         exclude_pattern=self.hash_filename_filter)
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
            self.hash_file_most_current = HashFile(
                    self, os.path.join(self.root_dir,
                                       f"{self.root_dir_name}_most_current_"
                                       f"{time.strftime('%Y-%m-%d')}.{used_algos[0]}"))
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
                combined_path = os.path.normpath(os.path.join(hash_file.hash_file_dir, file_path))
                if single_algo:
                    self.hash_file_most_current.set_hash_for_file(combined_path, hash_str)
                else:
                    self.hash_file_most_current.set_hash_for_file(hash_type, combined_path, hash_str)

    def do_incremental_checksums(self, algo_name, whitelist=None, blacklist=None):
        """
        Creates checksums for all changed files (that dont match checksums in
        hash_file_most_current)
        """
        if whitelist is not None and blacklist is not None:
            logger.error("Can only use either a whitelist or blacklist - not both!")
            return None
        if not self.hash_file_most_current:
            self.build_most_current()

        incremental = HashFile(
                self, os.path.join(self.root_dir, f"{self.root_dir_name}_"
                                                  f"{time.strftime('%Y-%m-%d')}.{algo_name}"))

        for dirpath, dirnames, fnames in os.walk(self.root_dir):
            for fname in fnames:
                file_path = os.path.join(dirpath, fname)
                rel_fpath = file_path.replace(self.root_dir + os.sep, '', 1)
                # exclude own logs
                if fname == LOG_BASENAME or (
                        fname.startswith(LOG_BASENAME + '.') and
                        fname.split(LOG_BASENAME + '.', 1)[1].isdigit()):
                    continue
                elif whitelist and not any(wildcard_match(pat, rel_fpath) for pat in whitelist):
                    # if we have a whitelist only include files that match one of the whitelist
                    # patterns
                    continue
                elif blacklist and any(wildcard_match(pat, rel_fpath) for pat in blacklist):
                    # if we have a blacklist only include files that dont match one of the
                    # blacklisted patterns
                    continue

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
        # fpath is an absolute path
        old_hash, hash_algo_str = self.hash_file_most_current.get_hash_by_file_path(
                                  file_path)
        if old_hash is None:
            new_hash = gen_hash_from_file(file_path, algo_name)
            include = True
        else:
            # when building incremental hashfile we have to use
            # the hash type for which we have A HASH in most_current
            # to find out if file changed -> changed -> use new hash type
            new_hash = gen_hash_from_file(file_path, hash_algo_str)
            if new_hash == old_hash:
                logger.debug("Old and new hashes match for file %s!", file_path)
                include = self.options["include_unchanged_files_incremental"]
            else:
                logger.info("File \"%s\" changed, a new hash was generated!", file_path)
                include = True

            if algo_name != hash_algo_str:
                logger.debug("Last hash used %s as algorithm -> generating "
                             "new hash with %s!", hash_algo_str, algo_name)
                new_hash = gen_hash_from_file(file_path, algo_name)
                include = True

        return new_hash, include

    def write_most_current(self):
        if not self.hash_file_most_current:
            self.build_most_current()
        self.hash_file_most_current.write()

    def sort_hash_files_by_mtime(self):
        self.all_hash_files = sorted(self.all_hash_files, key=lambda x: x.mtime)

    def check_missing_files(self):
        """
        Check if all files in subdirs of root_dir are represented in hash_file_most_current
        """
        if not self.hash_file_most_current:
            self.build_most_current()

        file_paths = self.hash_file_most_current.filename_hash_dict.keys()
        all_files = set()
        dirs = set()
        # add root dir
        dirs.add(self.root_dir)
        # account for a filename filter or dir without files and just subdirs
        # causing dirpath not being in dirs but deleting it from dirnames means
        # that we dont descend into any subdirs of that folder either
        # -> create set of all directory paths (and all of its sub-paths (dirs leading up to dir) to
        # account for dirs without (checksummed) files)
        for fp in file_paths:
            # normalize path so the check for ..path in dirs.. later works properly
            dirname = os.path.dirname(os.path.normpath(fp))
            while dirname != self.root_dir:
                dirs.add(dirname)
                dirname = os.path.dirname(dirname)

        missing_dirs = []

        for dirpath, dirnames, fnames in os.walk(self.root_dir):
            dirnames_filtered = []
            for dn in dirnames:
                # dirpath is path to current dir
                # use normpath to remove ./ or .\ at start of path, relpath also works
                dirpath_dirname = os.path.normpath(os.path.join(dirpath, dn))

                # filter out directories that dont contain any checksummed files
                if dirpath_dirname not in dirs:
                    missing_dirs.append(dirpath_dirname)
                else:
                    # IMPORTANT append dirname not combined dirpath and name!
                    dirnames_filtered.append(dn)

            dirnames[:] = dirnames_filtered

            for fname in fnames:
                # normpath otherwise generated file paths might be different
                # even though they point to the same location
                file_path = os.path.normpath(os.path.join(dirpath, fname))
                all_files.add(file_path)

        missing_files = all_files - file_paths
        if missing_dirs or missing_files:
            print("!!! NOT CHECKED IF CHECKSUMS STILL MATCH THE FILES !!!")
            print("Directories (D - where all files including subdirs are missing checksums) "
                  "and files (F) without checksum (paths are relative to path specified on "
                  "command line):")
            # convert to relative paths here
            missing_format = [f"D    {os.path.relpath(dp, start=self.root_dir)}"
                              for dp in missing_dirs]
            missing_format.extend((f"F    {os.path.relpath(fp, start=self.root_dir)}"
                                   for fp in sorted(missing_files)))
            print("\n".join(missing_format))

    def move_files(self, source_path, mv_path):
        # error when trying to move to diff drive
        if os.path.isabs(mv_path) and (
                os.path.splitdrive(source_path)[0].lower() !=
                os.path.splitdrive(mv_path)[0].lower()):
            logger.error("Can't move files to a different drive than the hash files "
                         "that hold their hashes!")
            return None
        if not self.hash_files_initialized():
            self.read_all_hash_files()

        # abspath basically just does join(os.getcwd(), path) if path isabs is False
        source_path = (source_path if os.path.isabs(source_path)
                       else os.path.join(self.root_dir, source_path))
        source_path = os.path.normpath(source_path)
        src_is_dir = os.path.isdir(source_path)
        # os.path.exists also accepts absolute paths with .. and . in them
        # >>> os.path.exists(r"N:\_archive\test\..\.\..\_archive")
        # True
        # can use normpath and a join to essentially do the same as move_fpath since it
        # removes redundant separators and up-level refs:
        # only works like that on dirs, on files we have to remove filename and then
        # join and test if mv path ends in a filenam?
        # >>> os.path.normpath(os.path.join(r"N:\_archive\test", r"..\.\..\_archive"))
        # 'N:\\_archive'
        # may change the meaning of a path that contains symbolic links
        dest_path = mv_path if os.path.isabs(mv_path) else os.path.join(self.root_dir, mv_path)
        dest_path = os.path.normpath(dest_path)
        dest_exists = os.path.exists(dest_path)
        dest_is_dir = False if not dest_exists else os.path.isdir(dest_path)
        if dest_exists and not dest_is_dir:
            logger.error("File %s already exists!", dest_path)
            return None

        # if source_path is a dir check if we need to relocate a hash file
        if src_is_dir:
            # relocate path of hash files later since we might be moving a dir into a dir and we
            # don't know the correct dest_path yet; but we could check for that with
            # if src_is_dir and dest_is_dir: and then append the basename of source_path
            # to dest_path
            # NOTE(m): We need to search for hash files in the dir we're moving recursively but
            #          we actually need to relocate or at least read them in as HashFile before
            #          the move, otherwise the relative paths won't match anymore!
            #          Can't do this by looping over self.all_hash_files since the files that
            #          need relocation might not be in there due to filters or a depth limit

            # set containing all paths of hash files that were already read into self.all_hash_files
            all_hash_files_paths = {hf.get_path() for hf in self.all_hash_files}
            # all hash files that we have to move with hash files that were already in
            # self.all_hash_files filtered out
            hash_files_to_move = [HashFile(self, os.path.normpath(hfile_path))
                                  for hfile_path in discover_hash_files(source_path, depth=-1)
                                  if os.path.normpath(hfile_path) not in all_hash_files_paths]
            # IMPORTANT read the hash files that were not in self.all_hash_files
            for hf in hash_files_to_move:
                hf.read()
        # check if the file we're moving is a hash file and if it's not in self.all_hash_files
        else:
            hash_files_to_move = ([HashFile(self, source_path)]
                                  if source_path.rsplit('.', 1)[1] in HASH_FILE_EXTENSIONS
                                     and source_path not in
                                     [hf.get_path() for hf in self.all_hash_files]
                                  else [])

        # Recursively move a file or directory (src) to another location (dst)
        # and return the destination.
        # If the destination is an existing directory, then src is moved inside that
        # directory. If the destination already exists but is not a directory, it may
        # be overwritten depending on os.rename() semantics.
        # path returned is the path of the file or folder that was moved so
        # if we move a dir to an existing dir we move the dir into the existing dir:
        # shutil.move("dir", "into") -> 'into\\dir' is returned
        dest_path = shutil.move(source_path, dest_path)

        for hash_file in self.all_hash_files:
            if src_is_dir:
                moved_fn_hash_dict = {}
                for fpath, hash_str in hash_file.filename_hash_dict.items():
                    if fpath.startswith(source_path):
                        # remove source_path from fpath and replace it with dest
                        moved = fpath.replace(source_path, dest_path)
                        moved_fn_hash_dict[moved] = hash_str
                    else:
                        moved_fn_hash_dict[fpath] = hash_str
                # replace with new fn hash dict
                hash_file.filename_hash_dict = moved_fn_hash_dict
            else:
                # save hash and del old path entry and replace it with new path
                hash_str, _ = hash_file.get_hash_by_file_path(source_path)
                # not present in hash_file
                if hash_str is None:
                    continue

                del hash_file[source_path]
                # even if file was moved INTO dir we can use dest_path without modification
                # since shutil.move returned the direct path to the file it moved
                hash_file.set_hash_for_file(dest_path, hash_str)

            # check if hash_file was also moved
            if hash_file.get_path().startswith(source_path):
                # we already got the path pointing directly to the moved file/dir from
                # shutil.move even if the target was a dir
                if src_is_dir:
                    hash_file.relocate(hash_file.get_path().replace(source_path, dest_path))
                else:
                    hash_file.relocate(dest_path)
            hash_file.write(force=True)

        # move additional hash files that were not in self.all_hash_files
        for hash_file in hash_files_to_move:
            # we already got the path pointing directly to the moved file/dir from
            # shutil.move even if the target was a dir
            if src_is_dir:
                hash_file.relocate(hash_file.get_path().replace(source_path, dest_path))
            else:
                hash_file.relocate(dest_path)
            hash_file.write(force=True)


class HashFile:
    def __init__(self, handling_checksumhelper, path_to_hash_file):
        self.handling_checksumhelper = handling_checksumhelper
        # store location of file (or use filename to build loc)
        # so we can build the path to files from root_dir correctly
        # from path in hash file
        # make sure we get an absolute path
        self.hash_file_dir, self.filename = os.path.split(os.path.normpath(os.path.abspath(path_to_hash_file)))
        # i dont thik ill ever need this
        # self.hash_filename_dict = {}
        self.filename_hash_dict = {}
        self.mtime = None
        # path to dir of hash file -> relpath from self.handling_checksumhelper.root_dir
        # since we set cwd to self.handling_checksumhelper.root_dir
        self.hash_type = self.filename.rsplit(".", 1)[-1]

    def __eq__(self, other):
        """
        Behaviour for '==' operator
        """
        try:
            return self.get_path() == other.get_path()
        except AttributeError:
            return False

    def __contains__(self, file_path):
        return os.path.normpath(file_path) in self.filename_hash_dict

    def __iter__(self):
        return iter(self.filename_hash_dict)

    def __len__(self):
        return len(self.filename_hash_dict)

    def __delitem__(self, file_path):
        """
        Pass in file_path (normalized here using normpath) to delete hash from hash file

        :param file_path: Absolute path to hashed file
        :return: Tuple of hash in hex and name of used hash algorithm
        """
        try:
            # filename_hash_dict uses normalized paths as keys
            del self.filename_hash_dict[os.path.normpath(file_path)]
        except KeyError:
            return False
        else:
            return True

    def get_hash_by_file_path(self, file_path):
        """
        Pass in file_path (normalized here using normpath) to get stored hash for
        that path
        KeyError -> None

        :param file_path: Absolute path to hashed file
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

        :param file_path: Absolute path to hashed file
                          gets normalized here
        :param hash_str:  Hex-string representation of file hash
        """
        self.filename_hash_dict[os.path.normpath(file_path)] = hash_str

    def get_path(self):
        return os.path.join(self.hash_file_dir, self.filename)

    def read(self):
        self.mtime = os.stat(self.get_path()).st_mtime
        # first line had \ufeff which is the BOM for utf-8 with bom
        with open(self.get_path(), "r", encoding="UTF-8-SIG") as f:
            # .lstrip(u'\ufeff')
            # ^ remove BOM (byte order mark) char at beginning of document
            # present if its UTF-8 with BOM - below does the same
            # use 'utf-8-sig', which expects and strips off the UTF-8 Byte Order Mark, which
            # is what shows up as ï»¿.
            try:
                text = f.read()
            except UnicodeDecodeError:
                # utf-8 couldnt decode file try ANSI encoding
                # which is "cp1252" on my system
                # re-assigning f should work since were opening the same file in the same
                # process but to be extra safe use a new var
                af = open(self.get_path(), "r", encoding="cp1252")
                text = af.read()
                # context manager doesnt work now so close file manually
                af.close()

        warned_abspath = False
        for ln in text.splitlines():
            # TODO(m): support text mode?
            # from GNU *sum utils:
            # default mode is to print a line with checksum, a character
            # indicating input mode ('*' for binary, space for text), and name
            # for each FILE.
            try:
                hash_str, file_path = ln.strip().split(" *", 1)
            except ValueError:
                logger.warning("Invalid line in hash file: %s", self.get_path())
                continue

            # alert on abspath in file; we use abspath internally but only write
            # relative paths to file
            if os.path.isabs(file_path):
                if not warned_abspath:
                    logger.warning("Found absolute path in hash file: %s", self.get_path())
                    warned_abspath = True
                # if drive letters dont match abort and let user handle this manually
                if (os.path.splitdrive(self.get_path())[0].lower() !=
                        os.path.splitdrive(file_path)[0].lower()):
                    raise AbspathDrivesDontMatch(
                            "Drive letters of the hash file "
                            f"'{os.path.abspath(self.get_path())}' and the absolute path "
                            f"'{file_path}' don't match! This needs to be fixed manually!")

            # use normpath here to ensure that paths get normalized
            # since we use them as keys
            abs_normed_path = os.path.normpath(os.path.join(self.hash_file_dir, file_path))
            self.filename_hash_dict[abs_normed_path] = hash_str

    def write(self, force=False):
        if force or cli_yes_no(f"Do you want to write {self.get_path()}?"):
            # convert absolute paths to paths that are relative to the hash file location
            abs_filename_hash_dict = {os.path.relpath(fp, start=self.hash_file_dir): hash_str
                                      for fp, hash_str in self.filename_hash_dict.items()}
            hashfile_str = build_hashfile_str(*abs_filename_hash_dict.items())
            # TotalCommander needs UTF-8 BOM for checksum files so use UTF-8-SIG
            with open(self.get_path(), "w", encoding="UTF-8-SIG") as w:
                w.write(hashfile_str)
            return True
        return False

    def relocate(self, mv_path):
        # error when trying to move to diff drive
        if os.path.isabs(mv_path) and (
                os.path.splitdrive(self.hash_file_dir)[0].lower() !=
                os.path.splitdrive(mv_path)[0].lower()):
            logger.error("Can't move hash file to a different drive than the files it contains "
                         "hashes for!")
            return None
        # need to check that we dont get None from move_fpath
        new_moved_path = move_fpath(self.get_path(), mv_path)
        if new_moved_path is None:
            logger.error("Couldn't move file due to a faulty move path!")
            return None
        new_hash_file_dir, new_filename = os.path.split(new_moved_path)

        # we dont need to modify our file paths in self.filename_hash_dict since
        # we're using absolute paths anyway
        self.hash_file_dir, self.filename = new_hash_file_dir, new_filename
        return new_hash_file_dir, new_filename
    
    def copy_to(self, mv_path):
        new_hash_file_dir, new_filename = self.relocate(mv_path)
        if self.write(force=True):
            logger.info("Copied hash file to %s", os.path.join(new_hash_file_dir, new_filename))
        else:
            logger.warning("Hash file was NOT copied!")

    def update_from_dict(self, update_dict):
        # TODO(moe): check if dict matches setup of filename_hash_dict
        self.filename_hash_dict.update(update_dict)

    def filter_deleted_files(self):
        self.filename_hash_dict = {fname: hash_str for fname, hash_str
                                   in self.filename_hash_dict.items() if os.path.isfile(fname)}

    def verify(self, whitelist=None):
        crc_errors = []
        missing = []
        matches = 0
        if not self.filename_hash_dict:
            logger.info("There were no hashes to verify!")
            return crc_errors, missing, matches

        for fpath, expected_hash in self.filename_hash_dict.items():
            # relative path for reporting and whitelisting
            # use replace instead of os.path.relpath since the latter is way slower
            # replace: 0.0263266 relpath: 2.5808342 in timeit with number=100
            # and working on a list of 500 paths per execution
            rel_fpath = fpath.replace(self.hash_file_dir + os.sep, "", 1)
            if whitelist:
                # skip file if we have a whitelist and there's no match
                if not any(wildcard_match(pattern, rel_fpath) for pattern in whitelist):
                    continue

            current = gen_hash_from_file(fpath, self.hash_type)
            if current is None:
                missing.append(rel_fpath)
                logger.warning("%s: MISSING", rel_fpath)
            elif expected_hash == current:
                matches += 1
                logger.info("%s: OK", rel_fpath)
            else:
                crc_errors.append(rel_fpath)
                logger.warning("%s: FAILED", rel_fpath)

        hf_path = os.path.join(self.hash_file_dir, self.filename)
        if matches and not crc_errors and not missing:
            logger.info("%s: No missing files and all files matching their hashes", hf_path)
        else:
            if matches and not crc_errors:
                logger.info("%s: All files matching their hashes!", hf_path)
            else:
                logger.warning("%s: %d files with wrong CRCs!", hf_path, len(crc_errors))
            if not missing:
                logger.info("%s: No missing files!", hf_path)
            else:
                logger.warning("%s: %d missing files!", hf_path, len(missing))
        return crc_errors, missing, matches


class MixedAlgoHashCollection:
    def __init__(self, handling_checksumhelper):
        self.handling_checksumhelper = handling_checksumhelper
        self.root_dir = self.handling_checksumhelper.root_dir
        self.filename_hash_dict = {}

    def __contains__(self, file_path):
        return os.path.normpath(file_path) in self.filename_hash_dict

    def __iter__(self):
        return iter(self.filename_hash_dict)

    def __len__(self):
        return len(self.filename_hash_dict)

    def __delitem__(self, file_path):
        """
        Pass in file_path (normalized here using normpath) to delete hash from hash file

        :param file_path: Absolute path to hashed file
        :return: Tuple of hash in hex and name of used hash algorithm
        """
        try:
            # filename_hash_dict uses normalized paths as keys
            del self.filename_hash_dict[os.path.normpath(file_path)]
        except KeyError:
            return False
        else:
            return True

    def set_hash_for_file(self, algo, file_path, hash_str):
        """
        Sets hash value in HashFile for specified file_path

        :param algo: Name string of used hash algorithm
        :param file_path: Absolute path to file
                          gets normalized here
        :param hash_str:  Hex-string representation of file hash
        """
        self.filename_hash_dict[os.path.normpath(file_path)] = (hash_str, algo)

    def get_hash_by_file_path(self, file_path):
        """
        Pass in file_path (normalized here using normpath) to get stored hash for
        that path
        KeyError -> None

        :param file_path: Absolute path to file
        :return: Tuple of hash in hex and name of used hash algorithm
        """
        # filename_hash_dict uses normalized paths as keys
        file_path = os.path.normpath(file_path)
        try:
            return self.filename_hash_dict[file_path]
        except KeyError:
            return None, None

    def to_single_hash_file(self, name, convert_algo_name):
        most_current_single = HashFile(self.handling_checksumhelper, name)
        # file_path is key and use () to also unpack value which is a 2-tuple
        for file_path, (hash_str, algo_name) in self.filename_hash_dict.items():
            if algo_name != convert_algo_name:
                # verify stored hash using old algo still matches
                new_hash = gen_hash_from_file(file_path, algo_name)
                if new_hash != hash_str:
                    logger.warning("File doesnt match most current hash: %s!", hash_str)
                new_hash = gen_hash_from_file(file_path, convert_algo_name)

                most_current_single.set_hash_for_file(file_path, new_hash)
            else:
                most_current_single.set_hash_for_file(file_path, hash_str)

        return most_current_single

    def verify(self, whitelist=None):
        # @Duplicate almost duplicate of HashFile.verify
        crc_errors = []
        missing = []
        matches = 0
        if not self.filename_hash_dict:
            logger.info("There were no hashes to verify!")
            return crc_errors, missing, matches

        for fpath, (expected_hash, hash_algo) in self.filename_hash_dict.items():
            # relative path for reporting and whitelisting
            # use replace instead of os.path.relpath since the latter is way slower
            # replace: 0.0263266 relpath: 2.5808342 in timeit with number=100
            # and working on a list of 500 paths per execution
            rel_fpath = fpath.replace(self.root_dir + os.sep, "", 1)
            if whitelist:
                # skip file if we have a whitelist and there's no match
                if not any(wildcard_match(pattern, rel_fpath) for pattern in whitelist):
                    continue

            current = gen_hash_from_file(fpath, hash_algo)
            if current is None:
                missing.append(rel_fpath)
                logger.warning("%s: MISSING", rel_fpath)
            elif expected_hash == current:
                matches += 1
                logger.info("%s: %s OK", rel_fpath, hash_algo.upper())
            else:
                crc_errors.append(rel_fpath)
                logger.warning("%s: %s FAILED", rel_fpath, hash_algo.upper())

        if matches and not crc_errors and not missing:
            logger.info("No missing files and all files matching their hashes")
        else:
            if matches and not crc_errors:
                logger.info("All files matching their hashes!")
            else:
                logger.warning("%d files with wrong CRCs!", len(crc_errors))
            if not missing:
                logger.info("No missing files!")
            else:
                logger.warning("%d missing files!", len(missing))
        return crc_errors, missing, matches


class AbspathDrivesDontMatch(Exception):
    def __init__(self, *args, **kwargs):
        # first arg is normally msg
        super().__init__(*args, **kwargs)


def _cl_check_missing(args):
    c = ChecksumHelper(args.path,
                       hash_filename_filter=args.hash_filename_filter)
    print("ATTENTION! By default ChecksumHelper finds all checksum files in "
          "sub-folders, if you want to limit the depth use the parameter -d")
    c.options["discover_hash_files_depth"] = args.discover_hash_files_depth
    c.check_missing_files()


def _cl_incremental(args):
    c = ChecksumHelper(args.path,
                       hash_filename_filter=args.hash_filename_filter)
    c.options["include_unchanged_files_incremental"] = False if args.filter_unchanged else True
    c.options["discover_hash_files_depth"] = args.discover_hash_files_depth
    c.do_incremental_checksums(args.hash_algorithm, whitelist=args.whitelist,
                               blacklist=args.blacklist)


def _cl_build_most_current(args):
    c = ChecksumHelper(args.path,
                       hash_filename_filter=args.hash_filename_filter)
    c.options["discover_hash_files_depth"] = args.discover_hash_files_depth
    c.build_most_current()
    if isinstance(c.hash_file_most_current, MixedAlgoHashCollection):
        c.hash_file_most_current = c.hash_file_most_current.to_single_hash_file(
                                   f"{c.root_dir}\\{c.root_dir_name}_most_current_"
                                   f"{time.strftime('%Y-%m-%d')}.{args.hash_algorithm}",
                                   args.hash_algorithm)
    if args.filter_deleted:
        c.hash_file_most_current.filter_deleted_files()
    c.hash_file_most_current.write()


def _cl_copy(args):
    h = HashFile(None, args.source_path)
    h.read()
    h.copy_to(args.dest_path)
    return h


def _cl_move(args):
    c = ChecksumHelper(args.root_dir, hash_filename_filter=args.hash_filename_filter)
    c.options["discover_hash_files_depth"] = args.discover_hash_files_depth
    c.move_files(args.source_path, args.mv_path)


def _cl_verify_all(args):
    nr_crc_errors = 0
    nr_missing = 0
    nr_matches = 0
    files_total = 0
    # verify all found hashes of discovered hash files for all supplied paths
    for root_p in args.root_dir:
        c = ChecksumHelper(root_p, hash_filename_filter=args.hash_filename_filter)
        c.options["discover_hash_files_depth"] = args.discover_hash_files_depth
        c.build_most_current()
        # hash_file_most_current can either be of type HashFile or MixedAlgoHashCollection
        crc_errors, missing, matches = c.hash_file_most_current.verify()
        nr_crc_errors += len(crc_errors)
        nr_missing += len(missing)
        nr_matches += matches
        files_total += len(c.hash_file_most_current.filename_hash_dict)
    print("\nVerified folders: %s" % (", ".join(args.root_dir),))
    print("    SUMMARY:")
    print("    TOTAL FILES:", files_total)
    print("    MATCHES:", nr_matches)
    print("    CRC ERRORS:", nr_crc_errors)
    print("    MISSING:", nr_missing)
    return files_total, nr_matches, nr_missing, nr_crc_errors


def _cl_verify_hfile(args):
    nr_crc_errors = 0
    nr_missing = 0
    nr_matches = 0
    files_total = 0
    for hash_file in args.hash_file_name:
        h = HashFile(None, hash_file)
        h.read()
        crc_errors, missing, matches = h.verify()
        nr_crc_errors += len(crc_errors)
        nr_missing += len(missing)
        nr_matches += matches
        files_total += len(h.filename_hash_dict)
    print("\nVerified hash files: %s" % (", ".join(args.hash_file_name),))
    print("    SUMMARY:")
    print("    TOTAL FILES:", files_total)
    print("    MATCHES:", nr_matches)
    print("    CRC ERRORS:", nr_crc_errors)
    print("    MISSING:", nr_missing)
    return files_total, nr_matches, nr_missing, nr_crc_errors


def _cl_verify_filter(args):
    c = ChecksumHelper(args.root_dir, hash_filename_filter=args.hash_filename_filter)
    c.options["discover_hash_files_depth"] = args.discover_hash_files_depth
    c.build_most_current()
    # hash_file_most_current can either be of type HashFile or MixedAlgoHashCollection
    c.hash_file_most_current.verify(whitelist=args.filter)


# checking for change based mtimes -> save in own file format(txt)?
# -> NO since we always want to verify that old files (that shouldnt have changed)
# -> still match their checksums


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Combine discovered checksum files into "
                                                 "one with the most current checksums or "
                                                 "build a new incremental checksum file "
                                                 "for the specified dir and all subdirs")

    # save name of used subcmd in var subcmd
    subparsers = parser.add_subparsers(title='subcommands', description='valid subcommands',
                                       dest="subcmd")
    # add parser that is used as parent parser for all subcmd parsers so they can have common
    # options without adding arguments to each one
    parent_parser = argparse.ArgumentParser(add_help=False)
    # all subcmd parsers will have options added here (as long as they have this parser as
    # parent)
    # metavar is name used placeholder in help text
    parent_parser.add_argument("-hf", "--hash-filename-filter", nargs="+", metavar="PATTERN",
                               help="Wildcard pattern for hash filenames that will be excluded "
                                    "from search",
                               type=str)
    parent_parser.add_argument("-d", "--discover-hash-files-depth", default=-1, type=int,
                               help="Number of subdirs to descend down to search for hash files; "
                                    "0 -> root dir only, -1 -> max depth; Default: -1",
                               metavar="DEPTH")

    incremental = subparsers.add_parser("incremental", aliases=["inc"], parents=[parent_parser],
                                        help="Discover hash files in subdirectories and verify"
                                             " found hashes and creating new hashes for new "
                                             "files! (So not truly incremental). New hashes "
                                             "(or all) will be written to file!")
    incremental.add_argument("path", type=str)
    incremental.add_argument("hash_algorithm", type=str)
    incremental.add_argument("-fu", "--filter-unchanged", action="store_false",
                             help="Dont include the checksum of unchanged files in the output")
    # only either white or blacklist can be used at the same time - not both
    inc_wl_or_bl = incremental.add_mutually_exclusive_group()
    inc_wl_or_bl.add_argument("-wl", "--whitelist", nargs="+", metavar='PATTERN', default=None,
                              help="Only file paths matching one of the wildcard patterns "
                                   "will be hashed", type=str)
    inc_wl_or_bl.add_argument("-bl", "--blacklist", nargs="+", metavar='PATTERN', default=None,
                              help="Wildcard patterns matching file paths to exclude from hasing",
                              type=str)
    # set func to call when subcommand is used
    incremental.set_defaults(func=_cl_incremental)

    build_most_current = subparsers.add_parser("build-most-current", aliases=["build"],
                                               parents=[parent_parser],
                                               help="Discover hash files in subdirectories and "
                                                    "write the newest ones to file.")
    build_most_current.add_argument("path", type=str)
    build_most_current.add_argument("-alg", "--hash-algorithm", type=str, default="sha512",
                                    help="If most current hashes include mixed algorithms, "
                                         "the specified one will be used to re-do the hash",
                                         choices=("md5", "sha256", "sha512"))
    # store_true -> default false, when specified true <-> store_false reversed
    build_most_current.add_argument("-fd", "--filter-deleted", action="store_false",
                                    help="Dont filter out deleted files in most_current hash file")
    # set func to call when subcommand is used
    build_most_current.set_defaults(func=_cl_build_most_current)

    check_missing = subparsers.add_parser("check-missing", aliases=["check"],
                                          parents=[parent_parser],
                                          help="Check if all files in subdirectories have an"
                                               " accompanying hash in a hash file. Hashes won't"
                                               " be verified!")
    check_missing.add_argument("path", type=str)
    # set func to call when subcommand is used
    check_missing.set_defaults(func=_cl_check_missing)

    copy = subparsers.add_parser("copy", aliases=["cp"],
                                 help="Copy a hash file modifying the relative paths "
                                      "within accordingly so they are still valid.")
    copy.add_argument("source_path", type=str,
                      help="Path to the hash file that should be copied")
    copy.add_argument("dest_path", type=str,
                      help="Absolute or relative (to the source_path) path to the destination "
                           "of copied hash file (paths not ending in \\ or / are assumed to "
                           "be file paths!): e.g. C:\\test\\photos.sha512, C:\\test\\, "
                           "../test/photos.sha512, .\\..\\test2\\")
    # set func to call when subcommand is used
    copy.set_defaults(func=_cl_copy)

    move = subparsers.add_parser("move", aliases=["mv"], parents=[parent_parser],
                                 help="Copy a hash file modifying the relative paths "
                                      "within accordingly so they are still valid.")
    move.add_argument("root_dir", type=str,
                      help="Root directory where we look for hash files in subdirectories")
    move.add_argument("source_path", type=str,
                      help="Path to the file or folder that should be moved")
    move.add_argument("mv_path", type=str,
                      help="Absolute or relative path to the destination of copied hash file")
    # set func to call when subcommand is used
    move.set_defaults(func=_cl_move)

    # ------------ VERIFY SUBPARSER ----------------
    verify = subparsers.add_parser("verify", aliases=["vf"], parents=[parent_parser],
                                   help="Commands for verifying operations")
    # add subparser for verify modes since we can't combine all the modes in one command
    # without confusion
    verify_subcmds = verify.add_subparsers(title='verify',
                                           description='Commands for verfying operations',
                                           dest="verisubcmd")
    verify_all = verify_subcmds.add_parser("all", aliases=(), parents=[parent_parser],
                                           help="Discover all hash files and verify the most "
                                                "up-to-date file hashes found for given "
                                                "directories")
    verify_all.add_argument("root_dir", type=str, nargs='+',
                            help="Root directory where we look for hash files in subdirectories")
    # set func to call when subcommand is used
    verify_all.set_defaults(func=_cl_verify_all)

    verify_hfile = verify_subcmds.add_parser("hash_file", aliases=('hf',),
                                             help="Verify all files in the specified hash files")
    verify_hfile.add_argument("hash_file_name", type=str, nargs='+',
                              help="Path to hash file(s)")
    verify_hfile.set_defaults(func=_cl_verify_hfile)

    verify_filter = verify_subcmds.add_parser("filter", aliases=('f',), parents=[parent_parser],
                                              help="Verify all files that match one of the"
                                                   " supplied filters")
    verify_filter.add_argument("root_dir", type=str,
                               help="Root directory where we look for hash files in "
                                    "subdirectories")
    verify_filter.add_argument("filter", type=str, nargs='+',
                               help="Wildcard filters that should be matched against files to "
                                    "verify: ? matches any one char, * matches 0 or more chars")
    verify_filter.set_defaults(func=_cl_verify_filter)
    # ------------ END OF VERIFY SUBPARSER ----------------

    args = parser.parse_args()
    if len(sys.argv) == 1:
        # default to stdout, but stderr would be better (use sys.stderr, then exit(1))
        parser.print_help()
        sys.exit(0)
    args.func(args)
