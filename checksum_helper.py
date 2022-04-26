import sys
import os
import shutil
import time
import hashlib
import logging
import argparse
import glob
import binascii
import datetime
import enum
import copy

from dataclasses import dataclass, fields
from logging.handlers import RotatingFileHandler

from typing import (
    Optional, List, Union, Sequence, Tuple, overload, Literal, Iterable, cast,
    Dict, TypedDict, Set
)

MODULE_PATH = os.path.dirname(os.path.realpath(__file__))
LOG_BASENAME = "chsmhlpr.log"

LOG_LVL_VERBOSE = logging.INFO - 1
LOG_LVL_EXTRAVERBOSE = logging.INFO - 2
logging.addLevelName(LOG_LVL_VERBOSE, "INFOV")
logging.addLevelName(LOG_LVL_EXTRAVERBOSE, "INFOVV")


# logging function for new level
def infov(self, message, *args, **kws) -> None:
    if self.isEnabledFor(LOG_LVL_VERBOSE):
        # Yes, logger takes its '*args' as 'args'.
        self._log(LOG_LVL_VERBOSE, message, args, **kws) 
logging.Logger.infov = infov  # type: ignore


def infovv(self, message, *args, **kws) -> None:
    if self.isEnabledFor(LOG_LVL_EXTRAVERBOSE):
        self._log(LOG_LVL_EXTRAVERBOSE, message, args, **kws) 
logging.Logger.infovv = infovv  # type: ignore

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


def cli_yes_no(question_str: str) -> bool:
    ans = input(f"{question_str} y/n:\n")
    while True:
        if ans == "n":
            return False
        elif ans == "y":
            return True
        else:
            ans = input(f"\"{ans}\" was not a valid answer, type in \"y\" or \"n\":\n")


def wildcard_match(pattern: str, text: str, partial_match: bool = False) -> bool:
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

    # i: index into text; j: index into pattern
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
    if j == m or partial_match:
        return True
    return False


def split_path(path_str: str) -> Tuple[Optional[List[str]], Optional[str]]:
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


def move_fpath(abspath: str, mv_path: str) -> Optional[str]:
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


# _hex = ... so we use the default _hex=False when omitting _hex
@overload
def gen_hash_from_file(fname: str, hash_algo_str: str,
                       _hex: Literal[False] = ...) -> bytes: ...

@overload
def gen_hash_from_file(fname: str, hash_algo_str: str,
                       _hex: Literal[True]) -> str: ...

def gen_hash_from_file(fname: str, hash_algo_str: str, _hex: bool=False) -> Union[str, bytes]:
    # construct a hash object by calling the appropriate constructor function
    hash_obj = hashlib.new(hash_algo_str)
    # open file in read-only byte-mode
    with open(fname, "rb") as f:
        # only read in chunks of size 4096 bytes
        chunk = f.read(4096)
        while chunk:
            # update it with the data by calling update() on the object
            # as many times as you need to iteratively update the hash
            hash_obj.update(chunk)
            chunk = f.read(4096)
        # using the lambda was slower (~30-40ms) for ~586 files
        # for chunk in iter(lambda: f.read(4096), b""):

    # get digest out of the object by calling digest() (or hexdigest() for hex-encoded string)
    if _hex:
        return hash_obj.hexdigest()
    else:
        return hash_obj.digest()


# for varags *args only the type of the first item needs to be specified
def build_hashfile_str(filename_hash_pairs: Iterable[Tuple[str, str]]) -> str:
    final_str_ln = []
    for hash_fname, hash_str in filename_hash_pairs:
        final_str_ln.append(f"{hash_str} *{hash_fname}")

    # end in newline since POSIX defines a line as: A sequence of zero or more
    # non- <newline> characters plus a terminating <newline> character
    return "\n".join(final_str_ln) + '\n'


HASH_FILE_EXTENSIONS = {algo for algo in hashlib.algorithms_available}
HASH_FILE_EXTENSIONS.add('cshd')
# forgot the comma again for single value tuple!!!!!!
# dirs starting with a substring in the tuple below will not be searched for hash files
DIR_START_STR_EXCLUDE = (".git",)


def discover_hash_files(start_path: str, depth: int = 2,
                        exclude_pattern: Optional[Sequence[str]]=None) -> List[str]:
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
                _, ext = fname.rsplit(".", 1)
                # replace works here for computing the relpath since all paths share
                # start_path (it's part of dirpath)
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


def descend_into(path: str, whitelist: Optional[List[str]]=None,
                 blacklist: Optional[List[str]]=None) -> bool:
    """
    Tests whether to descend into a directory based on its path
    expects that only one of white/blacklist is not None"""
    descend = True
    # NOTE: partial matches are only allowed for patterns in whitelist
    # (partial blacklist pattern matches still mean we have to descend into
    #  the matched dirpath e.g.: pattern: 'foo/bar/*.txt' dirpath: 'foo/bar/')
    #  only an exact match excludes the dir -> pattern: 'foo/bar/*' dirpath: 'foo/bar/')
    if whitelist and not any(wildcard_match(pat, path, partial_match=True) for pat in whitelist):
        # if we have a whitelist only descend into dirs that match or partially match
        # one of the whitelist patterns
        descend = False
    elif blacklist and any(wildcard_match(pat, path) for pat in blacklist):
        # if we have a blacklist only descend into dirs that dont match one of the
        # blacklisted patterns exactly
        descend = False

    return descend


def include_path(path: str, whitelist: Optional[List[str]]=None,
                 blacklist: Optional[List[str]]=None) -> bool:
    """expects that only one of white/blacklist is not None"""
    include = True
    if whitelist and not any(wildcard_match(pat, path) for pat in whitelist):
        # if we have a whitelist only include files that match one of the whitelist
        # patterns
        include = False
    elif blacklist and any(wildcard_match(pat, path) for pat in blacklist):
        # if we have a blacklist only include files that dont match one of the
        # blacklisted patterns
        include = False

    return include


def move_info(source_path: str, mv_path: str,
              root_dir: Optional[str] = None) -> Tuple[str, bool, str, bool, bool, str]:
    """Computes variables that are regularly need when doing copy/move operations
    root_dir parameter is used (like cwd in abspath) to make a relative path absolute
    (but with the option to specify a custom dir that differs from the cwd);
    default for root_dir is the cwd
    """
    if root_dir is None:
        root_dir = os.getcwd()
    # abspath basically just does join(os.getcwd(), path) if path isabs is False
    source_path = (source_path if os.path.isabs(source_path)
                   else os.path.join(root_dir, source_path))
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
    dest_path = mv_path if os.path.isabs(mv_path) else os.path.join(root_dir, mv_path)
    dest_path = os.path.normpath(dest_path)
    dest_exists = os.path.exists(dest_path)
    dest_is_dir = False if not dest_exists else os.path.isdir(dest_path)
    real_dest = os.path.join(dest_path, os.path.basename(source_path)) if dest_is_dir else dest_path

    return source_path, src_is_dir, dest_path, dest_exists, dest_is_dir, real_dest

CHOptions = TypedDict('CHOptions', {'include_unchanged_files_incremental': bool,
                                    'discover_hash_files_depth': int,
                                    'incremental_skip_unchanged': bool,
                                    'incremental_collect_fstat': bool})

class ChecksumHelper:

    hash_filename_filter: Sequence[str]

    def __init__(self, root_dir: str, hash_filename_filter: Optional[Union[str, Sequence[str]]]=None):
        self.root_dir: str = os.path.abspath(os.path.normpath(root_dir))
        self.root_dir_name: str = os.path.basename(self.root_dir)

        self.all_hash_files: List[ChecksumHelperData] = []
        # HashFile containing the most current hashes from all the combined hash
        # files that were found using discover_hash_files
        # -> also contains hashes for files that couldve been deleted
        self.hash_file_most_current: Optional[ChecksumHelperData] = None

        # susbtrings that cant be in filename of hash file
        if hash_filename_filter is None:
            self.hash_filename_filter = ()
        elif isinstance(hash_filename_filter, str):
            # ("md5") is NOT a tuple its a string ("md5",) IS a tuple (mind the comma!)
            if os.sep == "\\":
                # so windows users can use both / and \
                self.hash_filename_filter = (hash_filename_filter.replace(os.altsep, os.sep),)
            else:
                # unix doesnt have an os.altsep
                self.hash_filename_filter = (hash_filename_filter,)
        else:
            if os.sep == "\\":
                self.hash_filename_filter = tuple(s.replace(os.altsep, os.sep) for s in hash_filename_filter)
            else:
                self.hash_filename_filter = hash_filename_filter

        self.options: CHOptions = {
            "include_unchanged_files_incremental": True,
            "discover_hash_files_depth": -1,
            # TODO cl flags for these
            "incremental_skip_unchanged": False,
            "incremental_collect_fstat": True,
        }

    def discover_hash_files(self) -> None:
        hash_files = discover_hash_files(self.root_dir,
                                         depth=self.options["discover_hash_files_depth"],
                                         exclude_pattern=self.hash_filename_filter)
        self.all_hash_files = [ChecksumHelperData(self, hfile_path) for hfile_path in hash_files]

    def read_all_hash_files(self) -> None:
        if not self.all_hash_files:
            self.discover_hash_files()
        for hash_file in self.all_hash_files:
            hash_file.read()

    def hash_files_initialized(self) -> bool:
        return True if self.all_hash_files and all(
                hfile.entries for hfile in self.all_hash_files) else False

    def build_most_current(self) -> None:
        if not self.hash_files_initialized():
            self.read_all_hash_files()

        self.sort_hash_files_by_mtime()
        all_single_hash = True
        hash_types: Set[str] = set()
        for hf in self.all_hash_files:
            if not hf.single_hash:
                all_single_hash = False
                break
            hash_types.add(cast(str, hf.hash_type))

        if all_single_hash and len(hash_types) == 1:
            filename = os.path.join(
                self.root_dir,
                f"{self.root_dir_name}_most_current_"
                f"{time.strftime('%Y-%m-%d')}.{self.all_hash_files[0].hash_type}")
        else:
            filename = os.path.join(
                self.root_dir,
                f"{self.root_dir_name}_most_current_"
                f"{time.strftime('%Y-%m-%d')}.cshd")

        most_current = ChecksumHelperData(self, filename)
        # update dict with dicts from hash files -> sorted
        # dicts with biggest mtime last(newest) -> most current
        for cshd in self.all_hash_files:
            for file_path, hashed_file in cshd.entries.items():
                # since we add hashes from different files we have to combine the realtive
                # path IN the hashfile with the path TO the hashfile
                # to get a correct path
                combined_path = os.path.normpath(os.path.join(cshd.root_dir, file_path))
                most_current.set_entry(
                    combined_path,
                    HashedFile(
                        combined_path, hashed_file.mtime, hashed_file.hash_type,
                        hashed_file.hash_bytes, hashed_file.text_mode)
                )

        self.hash_file_most_current = most_current

    def do_incremental_checksums(
            self, algo_name, single_hash: bool = False, start_path: Optional[str] = None,
            root_only: bool = False, whitelist: Optional[List[str]] = None,
            blacklist: Optional[List[str]] = None) -> Optional['ChecksumHelperData']:
        """
        Creates checksums for all changed files (that dont match checksums in
        hash_file_most_current)

        start_path: has to be a subpath of self.root_dir
        root_only:  only do incremental checksums for the files of the root/start_path only
        """
        if whitelist is not None and blacklist is not None:
            logger.error("Can only use either a whitelist or blacklist - not both!")
            return None
        if not self.hash_file_most_current:
            self.build_most_current()

        if start_path is None:
            start_path = self.root_dir
        elif start_path and not start_path.startswith(self.root_dir + os.sep):
            logger.error("start_path has to be a subpath of the current ChecksumHelper's root dir")
            return None

        dir_name = os.path.basename(start_path)
        if single_hash:
            filename = os.path.join(start_path, f"{dir_name}_{time.strftime('%Y-%m-%d')}.{algo_name}")
        else:
            filename = os.path.join(start_path, f"{dir_name}_{time.strftime('%Y-%m-%d')}.cshd")
        incremental = ChecksumHelperData(self, filename)

        skip_unchanged = self.options['incremental_skip_unchanged']
        collect_fstat = self.options['incremental_collect_fstat']
        last_report = time.time()
        for dirpath, dirnames, fnames in os.walk(start_path):
            # filter dirnames before traversing into them
            dirnames[:] = [d for d in dirnames
                           if descend_into(os.path.join(dirpath[len(self.root_dir) + 1:], d),
                                           whitelist=whitelist, blacklist=blacklist)]

            for fname in fnames:
                file_path = os.path.join(dirpath, fname)

                # status report every N seconds
                if time.time() - last_report >= 30:
                    logger.info("STATUS: Checking file \"%s\"", file_path)
                    last_report = time.time()

                # replace works here for computing the relpath since all paths share
                # self.root_dir (it's part of dirpath)
                # rel_fpath = file_path[len(start_path) + 1:]
                # + 1 for last os.sep
                rel_from_root = file_path[len(self.root_dir) + 1:]
                # exclude own logs
                if fname == LOG_BASENAME or (
                        fname.startswith(LOG_BASENAME + '.') and
                        fname.split(LOG_BASENAME + '.', 1)[1].isdigit()):
                    continue
                # match white/blacklist against relative path starting from root dir
                # so it behaves correctly for different start_paths and it's
                # not confusing for the user
                if not include_path(rel_from_root, whitelist, blacklist):
                    continue

                include, hashed_file = self._build_verfiy_hash(file_path, algo_name,
                        collect_fstat=collect_fstat, skip_unchanged=skip_unchanged,
                        single_hash=single_hash)
                if include:
                    incremental.set_entry(file_path, cast(HashedFile, hashed_file))

            logger.infov("Finished hasing files in %s", dirpath)  # type: ignore
            if root_only:
                break

        return incremental

    def _build_verfiy_hash(
            self, file_path: str, algo_name: str, single_hash: bool = False,
            rehash_other_types: bool = True, collect_fstat: bool = True,
            skip_unchanged: bool = False) -> Tuple[bool, Optional['HashedFile']]:
        # NOTE: assumes self.hash_file_most_current is not None
        new: Optional['HashedFile'] = None
        include = False
        # fpath is an absolute path
        old = cast(ChecksumHelperData, self.hash_file_most_current).get_entry(file_path)
        if old is None:
            new_hash = HashedFile.compute_file_hash(file_path, algo_name)
            if new_hash is None:
                logger.warning("File '%s' will be skipped!", file_path)
                return False, None
            new = HashedFile(file_path, None, algo_name, new_hash, False)
            if collect_fstat:
                new.update_mtime()

            include = True
        else:
            # do a size/mtime comparison first if skip_unchanged and the same hash_type was used
            mtime: Optional[float] = None
            algos_match = old.hash_type == algo_name
            old_has_mtime = old.mtime is not None
            if collect_fstat or (skip_unchanged and old_has_mtime):
                mtime = HashedFile.fetch_mtime(file_path)

            # 0 match -1 current mtime is smaller/older 1 current mtime is bigger/younger
            comp_mtime: Optional[int] = None
            # # 0 match -1 current size is smaller 1 current size is bigger
            comp_size:  Optional[int] = None
            if old_has_mtime and mtime is not None:
                comp_mtime = (0 if old.mtime == mtime else
                              1 if cast(float, mtime) > cast(float, old.mtime) else -1)

            # we already compared the mtime so now we can update the mtime on old
            if not old_has_mtime and mtime is not None:
                old.mtime = mtime

            skip = False
            if skip_unchanged and comp_mtime == 0:
                include = self.options['include_unchanged_files_incremental']
                skip = True
                logger.infovv(  # type: ignore
                        "Skipping generation of a hash for file '%s' since the mtime matches!",
                        file_path)

            if not skip:
                # when building incremental hashfile we have to use
                # the hash type for which we have A HASH in most_current
                # to find out if file changed -> changed -> use new hash type
                current_hash = HashedFile.compute_file_hash(file_path, old.hash_type)
                if current_hash is None:
                    logger.warning("File '%s' will be skipped!", file_path)
                    return False, None

                # assume that we will be able to compute hashes after computing new_hash
                if current_hash == old.hash_bytes:
                    logger.infovv("Old and new hashes match for file %s!", file_path)  # type: ignore

                    # include if we didn't have an mtime before ONLY if we don't want
                    # to force a single hash file
                    if not old_has_mtime and mtime is not None and not single_hash:
                        include = True
                    # otherwise only if the option is set
                    else:
                        include = self.options["include_unchanged_files_incremental"]
                    new = old
                else:
                    if comp_mtime == 0:
                        logger.warning(
                            "Unexpected change of file hash, when modification time is "
                            "the same for file: %s", file_path)
                    elif comp_mtime == 1 or comp_mtime is None:
                        logger.info("File \"%s\" changed, a new hash was generated!", file_path)
                    elif comp_mtime == -1:
                        logger.info("File hashes don't match with the file on disk being older "
                                    "than the recorded modfication time! The hash of the file "
                                    "on disk will be used: %s", file_path)
                    include = True
                    new_hash = current_hash
            else:
                new = old

            if not algos_match and rehash_other_types:
                logger.infov("Recorded hash used %s as algorithm -> re-hashing "  # type: ignore
                             "with %s: %s!", old.hash_type, algo_name, file_path)
                new_hash = HashedFile.compute_file_hash(file_path, algo_name)
                new = None  # so below creates new HashedFile with different hash type
                include = True

            if include and new is None:
                new = HashedFile(file_path, mtime, algo_name, cast(bytes, new_hash), False)

        return include, new

    def write_most_current(self, hash_algo: str) -> None:
        if not self.hash_file_most_current:
            self.build_most_current()
        cast(ChecksumHelperData, self.hash_file_most_current).write()

    def sort_hash_files_by_mtime(self) -> None:
        self.all_hash_files = sorted(self.all_hash_files, key=lambda x: cast(float, x.mtime))

    def check_missing_files(self) -> None:
        """
        Check if all files in subdirs of root_dir are represented in hash_file_most_current
        """
        if not self.hash_file_most_current:
            self.build_most_current()

        file_paths = cast(ChecksumHelperData,
                          self.hash_file_most_current).entries.keys()
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

        missing_dirs_non_empty = []
        for d in missing_dirs:
            try:
                if len(os.listdir(d)) > 0:
                    missing_dirs_non_empty.append(d)
            except PermissionError:
                logger.info("Access denied while opening folder: %s", d)
            except FileNotFoundError:
                # folder was (re)moved
                pass

        if missing_dirs or missing_files:
            print("!!! NOT CHECKED IF CHECKSUMS STILL MATCH THE FILES !!!")
            print("Directories (D - where all files including subdirs are missing checksums) "
                  "and files (F) without checksum (paths are relative to path specified on "
                  "command line):")
            # convert to relative paths here
            missing_format = [f"D    {os.path.relpath(dp, start=self.root_dir)}"
                              for dp in missing_dirs_non_empty]
            missing_format.extend((f"F    {os.path.relpath(fp, start=self.root_dir)}"
                                   for fp in sorted(missing_files)))
            print("\n".join(missing_format))

    def move_files(self, source_path: str, mv_path: str) -> None:
        # error when trying to move to diff drive
        if os.path.isabs(mv_path) and (
                os.path.splitdrive(source_path)[0].lower() !=
                os.path.splitdrive(mv_path)[0].lower()):
            logger.error("Can't move files to a different drive than the hash files "
                         "that hold their hashes!")
            return None

        # make sure we're reading all the hash files by always using max depth
        # without a filename_filter (that's why we can't use self.all_hash_files)
        all_hash_files = []
        for hf_path in discover_hash_files(self.root_dir, depth=-1, exclude_pattern=None):
            cshd = ChecksumHelperData(self, hf_path)
            cshd.read()
            all_hash_files.append(cshd)

        (source_path, src_is_dir, dest_path, dest_exists,
            dest_is_dir, real_dest) = move_info(source_path, mv_path, root_dir=self.root_dir)

        real_dest_exists = os.path.exists(real_dest)
        # only checking for file conflict since for some systems overwriting might be the default
        if not src_is_dir and real_dest_exists:
            logger.error("File %s already exists!", real_dest)
            return None
        # NOTE(m): don't have to check for individual conflicts inside dirs, shutil.move
        #          only moves a dir if real_dest doesn't exist (thus we can't have any conflicts)

        # Recursively move a file or directory (src) to another location (dst)
        # and return the destination.
        # If the destination is an existing directory, then src is moved inside that
        # directory. If the destination already exists but is not a directory, it may
        # be overwritten depending on os.rename() semantics.
        # path returned is the path of the file or folder that was moved so
        # if we move a dir to an existing dir we move the dir into the existing dir:
        # shutil.move("dir", "into") -> 'into\\dir' is returned
        try:
            # shutil.move returns None if it's a rename OF a DIRECTORY in the CURRENT DIR
            mb_dest_path = shutil.move(source_path, dest_path)
            if mb_dest_path is not None:
                dest_path = mb_dest_path
        except shutil.Error as e:
            logger.error("Couldn't move file(s): %s", str(e))
            return None

        for chsd in all_hash_files:
            if src_is_dir:
                moved_fn_hash_dict = {}
                for fpath, hashed_file in chsd.entries.items():
                    if fpath.startswith(source_path):
                        # remove source_path from fpath and replace it with dest
                        moved = fpath.replace(source_path, dest_path)
                        moved_fn_hash_dict[moved] = hashed_file
                    else:
                        moved_fn_hash_dict[fpath] = hashed_file
                # replace with new fn hash dict
                chsd.entries = moved_fn_hash_dict
            else:
                # save hash and del old path entry and replace it with new path
                mb_hashed_file = chsd.get_entry(source_path)
                # present in hash_file (can't use continue here since we still might need to
                # relocate and write the hash file)
                if mb_hashed_file:
                    del chsd[source_path]
                    # even if file was moved INTO dir we can use dest_path without modification
                    # since shutil.move returned the direct path to the file it moved
                    chsd.set_entry(dest_path, mb_hashed_file)

            # check if hash_file was also moved
            if src_is_dir and chsd.get_path().startswith(source_path):
                # we already got the path pointing directly to the moved file/dir from
                # shutil.move even if the target was a dir
                    chsd.relocate(chsd.get_path().replace(source_path, dest_path))
            elif not src_is_dir and chsd.get_path() == source_path:
                    chsd.relocate(dest_path)
            chsd.write(force=True)


class ChecksumHelperData:

    root_dir: str
    filename: str

    def __init__(self, handling_checksumhelper, path_to_hash_file: str):
        self.handling_checksumhelper: ChecksumHelper = handling_checksumhelper
        # store location of file (or use filename to build loc)
        # so we can build the path to files from root_dir correctly
        # from path in hash file
        # make sure we get an absolute path
        self.root_dir, self.filename = os.path.split(
                os.path.normpath(os.path.abspath(path_to_hash_file)))
        # filename -> 'HashedFile' (filename is an absolute and normalized path)
        self.entries: Dict[str, 'HashedFile'] = {}
        self.mtime: Optional[float] = None
        _, ext = os.path.splitext(self.filename)
        # whether only one type of hash alogrithm is used
        self.single_hash: bool = False if not ext or ext == ".cshd" else True
        # None if self.single_hash is False
        self.hash_type: Optional[str] = self.filename.rsplit(".", 1)[1] if self.single_hash else None

    def __eq__(self, other):
        """
        Behaviour for '==' operator
        """
        try:
            return self.get_path() == other.get_path()
        except AttributeError:
            return False

    def __contains__(self, file_path: str) -> bool:
        return os.path.normpath(file_path) in self.entries

    def __iter__(self):
        return iter(self.entries)

    def __len__(self):
        return len(self.entries)

    def __delitem__(self, file_path: str) -> bool:
        """
        Pass in file_path (normalized here using normpath) to delete hash from hash file

        :param file_path: Absolute path to hashed file
        :return: Tuple of hash in hex and name of used hash algorithm
        """
        try:
            # self.entries uses normalized abspaths as keys
            del self.entries[os.path.normpath(file_path)]
        except KeyError:
            return False
        else:
            return True

    def get_entry(self, file_path: str) -> Optional['HashedFile']:
        """
        Pass in file_path (normalized here using normpath) to get stored hash for
        that path
        KeyError -> None

        :param file_path: Absolute path to hashed file
        :return: Tuple of hash in hex and name of used hash algorithm
        """
        # self.entries uses normalized abspaths as keys
        file_path = os.path.normpath(file_path)
        try:
            return self.entries[file_path]
        except KeyError:
            return None

    def set_entry(self, file_path: str, hashed_file: 'HashedFile') -> None:
        """
        Sets hash value in HashFile for specified file_path

        :param file_path: Absolute path to hashed file
                          gets normalized here
        :param hash_str:  Hex-string representation of file hash
        """
        self.entries[os.path.normpath(file_path)] = hashed_file

    def get_path(self) -> str:
        return os.path.join(self.root_dir, self.filename)

    def read(self) -> None:
        if self.single_hash:
            self._read_from_single_hash_file()
        else:
            self._read()

    def _read(self) -> None:
        try:
            self.mtime = os.stat(self.get_path()).st_mtime
        except (FileNotFoundError, PermissionError):
            logger.error("Could not access/find hash file '%s'", self.get_path())
            return

        with open(self.get_path(), "r", encoding="UTF-8") as f:
            text = f.read()

        warned_pardir_ref = False
        for ln in text.splitlines():
            stripped = ln.strip()

            mtime = None
            size = None
            try:
                mtime_end = stripped.index(",")
                if mtime_end != 0:
                    mtime = float(stripped[:mtime_end])

                hash_type_end = stripped.index(",", mtime_end + 1)
                hash_type = stripped[mtime_end + 1:hash_type_end]

                hash_str_end = stripped.index(" ", hash_type_end + 1)
                hash_str = stripped[hash_type_end + 1:hash_str_end]

                file_path = stripped[hash_str_end + 1:]
            except (ValueError, IndexError):
                logger.warning("Read failed: there were invalid lines in cshd file '%s'. ",
                               self.get_path())
                return

            # alert on abspath in file; we use abspath internally but only write
            # relative paths to file
            if os.path.isabs(file_path):
                logger.warning("Read failed! Found absolute path in hash file: %s", self.get_path())
                # even if drive letters match: drives could be from different computers
                # or could have been remounted
                return
            else:
                if not warned_pardir_ref and '..' + os.sep in os.path.normpath(file_path):
                    logger.warning("Found reference beyond the hash file's root dir in file: '%s'. "
                                   "Consider moving/copying the file using ChecksumHelper move/copy "
                                   "to the path that is the most common denominator!",
                                   self.get_path())
                    warned_pardir_ref = True

            # use normpath here to ensure that paths get normalized
            # since we use them as keys
            # also needed since we always use '/' as path sep when writing the file
            # but use os.sep while running (since unix can't deal with '\' as path sep)
            abs_normed_path = os.path.normpath(os.path.join(self.root_dir, file_path))
            self.entries[abs_normed_path] = HashedFile(
                    abs_normed_path, mtime, hash_type, binascii.a2b_hex(hash_str), False)

    def _read_from_single_hash_file(self) -> None:
        hash_type = self.hash_type
        try:
            self.mtime = os.stat(self.get_path()).st_mtime
        except (FileNotFoundError, PermissionError):
            logger.error("Could not access/find hash file '%s'", self.get_path())
            return

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

        warned_pardir_ref = False
        for ln in text.splitlines():
            # from GNU *sum utils:
            # default mode is to print a line with checksum, a character
            # indicating input mode ('*' for binary, space for text), and name
            # for each FILE.
            # NOTE: according to the manpage there is no difference between binary and
            # text mode on a GNU system (same is true for fopen from the C stdlib:
            # The character 'b' shall have no effect, but is allowed for ISO C standard conformance)
            stripped = ln.strip()

            try:
                first_space = stripped.index(" ")
                hash_str = stripped[:first_space]
                space_or_asterisk = stripped[first_space + 1]
                file_path = stripped[first_space + 2:]
            except (ValueError, IndexError):
                logger.warning("Read failed: there were invalid lines in hash file '%s'. "
                               "The correct format is:\n"
                               "[0-9a-fA-F]+ ( |*)[^/]+", self.get_path())
                return

            if space_or_asterisk == " ":
                text_mode = True
            elif space_or_asterisk == "*":
                text_mode = False
            else:
                logger.warning(
                    "Read failed: Expected either '*' or ' ' got '%s' in file %s",
                    space_or_asterisk, self.get_path())
                return

            # alert on abspath in file; we use abspath internally but only write
            # relative paths to file
            if os.path.isabs(file_path):
                logger.warning("Read failed! Found absolute path in hash file: %s", self.get_path())
                # even if drive letters match: drives could be from different computers
                # or could have been remounted
                return
            else:
                if not warned_pardir_ref and '..' + os.sep in os.path.normpath(file_path):
                    logger.warning("Found reference beyond the hash file's root dir in file: '%s'. "
                                   "Consider moving/copying the file using ChecksumHelper move/copy "
                                   "to the path that is the most common denominator!",
                                   self.get_path())
                    warned_pardir_ref = True


            # use normpath here to ensure that paths get normalized
            # since we use them as keys
            # also needed since we always use '/' as path sep when writing the file
            # but use os.sep while running (since unix can't deal with '\' as path sep)
            abs_normed_path = os.path.normpath(os.path.join(self.root_dir, file_path))
            self.entries[abs_normed_path] = HashedFile(
                    abs_normed_path, None, cast(str, hash_type), binascii.a2b_hex(hash_str), text_mode)

    def _check_write_file(self, force=False) -> bool:
        write_file = False
        if os.path.exists(self.get_path()) and not force:
            inp = input(f"Do you want to overwrite {self.get_path()} or should "
                        "the generated file be renamed(ren)? (y/n/ren): ").strip().lower()
            if inp == "y" or inp == "yes":
                write_file = True
            elif inp == "ren" or inp == "rename":
                write_file = True
                # splitext includes . in the extension part!!
                fn, ext = os.path.splitext(self.filename)
                # date is already ISO 8601 add time as well omitting ':' since it's a banned
                # char for windows filenames
                self.filename = f"{fn}T{time.strftime('%H%M%S')}{ext}"
        else:
            write_file = True

        return write_file

    def write(self, force: bool = False) -> bool:
        if not self.entries:
            logger.info("There are no hashed file entries to write!")
            return False

        fn, ext = os.path.splitext(self.filename)
        if ext == ".cshd":
            written = self._write(force)
        elif not ext or not self.single_hash:
            self.filename = f"{fn}.cshd"
            written = self._write(force)
        else:
            written = self._write_as_single_hash_file(force)

        if written:
            logger.info("Wrote %s", self.get_path())
        return written

    def _write(self, force=False) -> bool:
        write_file = self._check_write_file(force)
        if not write_file:
            return False

        root_dir = self.root_dir
        lines = []
        for file_path, hashed_file in self.entries.items():
            rel_file_path = os.path.relpath(file_path, start=root_dir)
            # NOTE: always use '/' as path sep when writing the file
            # but use os.sep while running (since unix can't deal with '\' as path sep)
            if os.sep == '\\':
                rel_file_path = rel_file_path.replace(os.sep, '/')
            lines.append(
                f"{hashed_file.mtime if hashed_file.mtime is not None else ''},"
                f"{hashed_file.hash_type},"
                f"{hashed_file.hex_hash()} {rel_file_path}")

        # we want universal newlines mode disabled here (translates \n to
        # platform default; it's fine for reading since everything ends
        # up as \n)
        with open(self.get_path(), "w", encoding="UTF-8", newline='') as w:
            w.write("\n".join(lines))
            w.write("\n")

        return True

    def _write_as_single_hash_file(self, force: bool = False) -> bool:
        assert self.single_hash

        write_file = self._check_write_file(force)
        if not write_file:
            return False

        root_dir = self.root_dir
        lines = []
        single_hash = self.single_hash
        for file_path, hashed_file in self.entries.items():
            # convert absolute paths to paths that are relative to the hash file location
            rel_file_path = os.path.relpath(file_path, start=root_dir)
            # NOTE: always use '/' as path sep when writing the file
            # but use os.sep while running (since unix can't deal with '\' as path sep)
            if os.sep == '\\':
                rel_file_path = rel_file_path.replace(os.sep, '/')

            lines.append(
                f"{hashed_file.hex_hash()} {' ' if hashed_file.text_mode else '*'}{rel_file_path}")

        # we want universal newlines mode disabled here (translates \n to
        # platform default; it's fine for reading since everything ends
        # up as \n)
        # older version of TotalCommander need UTF-8 BOM for checksum files so use UTF-8-SIG
        with open(self.get_path(), "w", encoding="UTF-8-SIG", newline='') as w:
            w.write("\n".join(lines))
            w.write("\n")

        return write_file

    def to_single_hash_file(self, hash_type: str) -> None:
        # if not self.single_hash:
        #     print("File contains multiple hash algorithms but is supposed to be "
        #           "written as conventional single hash file (*.md5, *.sha512 etc.).\n"
        #           "Guaranteed (on every python platform) hash algorithm names (RECOMMENDED):\n"
        #           f"{', '.join(hashlib.algorithms_available)}\n"
        #           "Additionally available hash algorithm names:\n"
        #           f"{', '.join(hashlib.algorithms_available - hashlib.algorithms_guaranteed)}\n")
        #     while convert_algo_name not in hashlib.algorithms_available:
        #         convert_algo_name = input(
        #             "\nEnter a hash algorithm name that all files that were hashed "
        #             "with another algorithm should be re-hashed with: ").strip()

        for file_path, hashed_file in self.entries.items():
            if hashed_file.hash_type != hash_type:
                # verify stored hash using old algo still matches
                new_hash = gen_hash_from_file(file_path, hashed_file.hash_type)
                if new_hash != hashed_file.hash_bytes:
                    logger.warning("File %s doesnt match most current hash: %s!",
                                   file_path, hashed_file.hex_hash())

                new_hash = gen_hash_from_file(file_path, hash_type)
                hashed_file.hash_type = hash_type
                hashed_file.hash_bytes = new_hash

        self.filename = f"{os.path.splitext(self.filename)[0]}.{hash_type}"
        self.single_hash = True
        self.hash_type = hash_type

    def relocate(self, mv_path: str) -> Tuple[Optional[str], Optional[str]]:
        """Converts mv_path into an absolut path and performing some additional checks
        whether the relocation is valid; Doesnt modfiy anthing in self.entires etc. unless
        the file was renamed to single hash file (e.g. '.sha512') then the hashed files
        in other hash types will be re-hashed"""
        # error when trying to move to diff drive
        if os.path.isabs(mv_path) and (
                os.path.splitdrive(self.root_dir)[0].lower() !=
                os.path.splitdrive(mv_path)[0].lower()):
            logger.error("Can't move hash file to a different drive than the files it contains "
                         "hashes for!")
            return None, None

        (source_path, src_is_dir, dest_path, dest_exists,
            dest_is_dir, real_dest) = move_info(self.get_path(), mv_path, root_dir=self.root_dir)

        new_hash_file_dir, new_filename = os.path.split(real_dest)
        _, ext = os.path.splitext(new_filename)
        if not ext or ext == ".cshd":
            self.single_hash = False
            self.hash_type = None
        else:
            hash_type = ext[1:]
            if hash_type not in hashlib.algorithms_available:
                logger.error("Could not rename file to have extension '%s' since it is not a "
                             "supported (by hashlib) hash algorithm!", hash_type)
                return None, None
            else:
                self.to_single_hash_file(hash_type)

        # we dont need to modify our file paths in self.entries since
        # we're using absolute paths anyway
        self.root_dir, self.filename = new_hash_file_dir, new_filename

        return new_hash_file_dir, new_filename
    
    def copy_to(self, mv_path: str) -> None:
        bu_root, bu_fn = self.root_dir, self.filename
        new_hash_file_dir, new_filename = self.relocate(mv_path)
        written = False
        if new_hash_file_dir is not None:
            written = self.write()

        if written:
            logger.info("Copied hash file to %s",
                        os.path.join(cast(str, new_hash_file_dir), cast(str, new_filename)))
        else:
            logger.warning("Hash file was NOT copied!")

        # restore old path
        self.root_dir, self.filename = bu_root, bu_fn

    def update_from_dict(self, update_dict: Dict[str, 'HashedFile']):
        self.entries.update(update_dict)

    def filter_deleted_files(self) -> None:
        self.entries = {fname: hash_str for fname, hash_str in self.entries.items()
                        if os.path.isfile(fname)}

    def verify(self, whitelist: Optional[Sequence[str]]=None) -> Tuple[List[Tuple[str, str]], List[str], int]:
        crc_errors: List[Tuple[str, str]] = []
        missing: List[str] = []
        matches = 0
        if not self.entries:
            logger.info("There were no hashes to verify!")
            return crc_errors, missing, matches

        for fpath, hashed_file in self.entries.items():
            # relative path for reporting and whitelisting
            # we have to use os.path.relpath even if its slow but replace fails if we have
            # relpaths that reference files in the pardir or up
            rel_fpath = os.path.relpath(fpath, start=self.root_dir)
            if whitelist:
                # skip file if we have a whitelist and there's no match
                if not any(wildcard_match(pattern, rel_fpath) for pattern in whitelist):
                    continue

            try:
                current: Optional[bytes] = gen_hash_from_file(fpath, hashed_file.hash_type)
            except FileNotFoundError:
                current = None
            except PermissionError:
                logger.warning("Permission to open file '%s' was denied!", fpath)
                current = None

            if current is None:
                missing.append(rel_fpath)
                logger.warning("%s: MISSING", rel_fpath)
            elif hashed_file.hash_bytes == current:
                matches += 1
                logger.info("%s: %s OK", rel_fpath, hashed_file.hash_type.upper())
            else:
                # give more information if we have mtime data
                if hashed_file.mtime is not None:
                    current_mtime = cast(float, hashed_file.fetch_mtime(hashed_file.filename))
                    if current_mtime > hashed_file.mtime:
                        logger.warning("%s: %s FAILED -> OUTDATED HASH (file is newer)",
                                       rel_fpath, hashed_file.hash_type.upper())
                        crc_errors.append(("OUTDATED HASH (file is newer)", rel_fpath))
                    elif current_mtime == hashed_file.mtime:
                        logger.error("%s: %s FAILED -> CORRUPTED (same modification time)",
                                     rel_fpath, hashed_file.hash_type.upper())
                        crc_errors.append(("CORRUPTED (same modification time)", rel_fpath))
                    else:
                        logger.warning("%s: %s FAILED -> OUTDATED HASH (file is older)",
                                       rel_fpath, hashed_file.hash_type.upper())
                        crc_errors.append(("OUTDATED HASH (file is older)", rel_fpath))
                else:
                    crc_errors.append(("", rel_fpath))
                    logger.warning("%s: %s FAILED", rel_fpath, hashed_file.hash_type.upper())

        if matches and not crc_errors and not missing:
            logger.info("%s: No missing files and all files matching their hashes", self.get_path())
        else:
            if matches and not crc_errors:
                logger.info("%s: All files matching their hashes!", self.get_path())
            else:
                logger.warning("%s: %d files with wrong CRCs!", self.get_path(), len(crc_errors))
            if not missing:
                logger.info("%s: No missing files!", self.get_path())
            else:
                logger.warning("%s: %d missing files!", self.get_path(), len(missing))
        return crc_errors, missing, matches


@dataclass
class HashedFile:
    __slots__ = ['filename', 'mtime', 'hash_type', 'hash_bytes', 'text_mode']

    # absolute path!
    filename: str
    mtime: Optional[float]
    hash_type: str
    hash_bytes: bytes
    # for compatability reasons
    text_mode: bool

    def meta_eql(self, o) -> bool:
        for field in fields(HashedFile):
            if getattr(self, field.name) != getattr(o, field.name):
                return False
        return True

    def hex_hash(self) -> str:
        # b2a_hex returns bytes string -> have to decode it as utf-8 to count as str
        return binascii.b2a_hex(self.hash_bytes).decode('utf-8')

    def mtime_str(self) -> Optional[str]:
        if self.mtime is None:
            return None
        else:
            return datetime.datetime.fromtimestamp(self.mtime).isoformat()

    @staticmethod
    def fetch_mtime(filename: str) -> Optional[float]:
        try:
            stat = os.stat(filename)
        except FileNotFoundError:
            logger.warning("Could not find file '%s' for getting file stats!", filename)
            result = None
        except PermissionError:
            logger.warning("Permission to stat the file was denied: %s!", filename)
            result = None
        else:
            result = stat.st_mtime

        return result

    def update_mtime(self) -> None:
        mb_mtime = HashedFile.fetch_mtime(self.filename)
        if mb_mtime is not None:
            self.mtime = mb_mtime

    @staticmethod
    def compute_file_hash(filename: str, hash_type: str) -> Optional[bytes]:
        try:
            result: Optional[bytes] = gen_hash_from_file(filename, hash_type)
        except FileNotFoundError:
            logger.warning("Could not find file '%s' for hashing!", filename)
            result = None
        except PermissionError:
            logger.warning("Permission to open the file for hashing was denied: %s!", filename)
            result = None

        return result

    def copy(self) -> 'HashedFile':
        return copy.copy(self)


def _cl_check_missing(args: argparse.Namespace) -> None:
    c = ChecksumHelper(args.path,
                       hash_filename_filter=args.hash_filename_filter)
    print("ATTENTION! By default ChecksumHelper finds all checksum files in "
          "sub-folders, if you want to limit the depth use the parameter -d")
    c.options["discover_hash_files_depth"] = args.discover_hash_files_depth
    c.check_missing_files()


def _cl_incremental(args: argparse.Namespace):
    c = ChecksumHelper(args.path,
                       hash_filename_filter=args.hash_filename_filter)
    c.options["include_unchanged_files_incremental"] = not args.dont_include_unchanged
    c.options["discover_hash_files_depth"] = args.discover_hash_files_depth
    c.options['incremental_skip_unchanged'] = args.skip_unchanged
    c.options['incremental_collect_fstat'] = not args.dont_collect_mtime

    if args.per_directory:
        incremental = c.do_incremental_checksums(
            args.hash_algorithm,
            single_hash=args.single_hash,
            root_only=True,
            whitelist=args.whitelist,
            blacklist=args.blacklist)
        if incremental is not None:
            incremental.write()

        for dp in os.listdir(args.path):
            if not os.path.isdir(os.path.join(args.path, dp)):
                continue

            dirpath = dp + os.sep
            if not include_path(dirpath, args.whitelist, args.blacklist):
                continue

            incremental = c.do_incremental_checksums(
                args.hash_algorithm,
                single_hash=args.single_hash,
                start_path=os.path.abspath(os.path.join(args.path, dp)),
                whitelist=args.whitelist,
                blacklist=args.blacklist)
            if incremental is not None:
                incremental.write()
    else:
        incremental = c.do_incremental_checksums(args.hash_algorithm, single_hash=args.single_hash,
                                                 whitelist=args.whitelist, blacklist=args.blacklist)
        if incremental is not None:
            if args.out_filename:
                incremental.relocate(args.out_filename)
            incremental.write()


def _cl_build_most_current(args: argparse.Namespace) -> None:
    c = ChecksumHelper(args.path,
                       hash_filename_filter=args.hash_filename_filter)
    c.options["discover_hash_files_depth"] = args.discover_hash_files_depth
    c.build_most_current()
    if c.hash_file_most_current:
        if not args.dont_filter_deleted:
            c.hash_file_most_current.filter_deleted_files()
        if args.out_filename:
            c.hash_file_most_current.relocate(args.out_filename)
        c.hash_file_most_current.write()
    else:
        logger.error("Could not build most current hash file data for: %s", args.path)


def _cl_copy(args: argparse.Namespace) -> ChecksumHelperData:
    cshd = ChecksumHelperData(None, args.source_path)
    cshd.read()
    cshd.copy_to(args.dest_path)
    return cshd


def _cl_move(args: argparse.Namespace) -> None:
    c = ChecksumHelper(args.root_dir, hash_filename_filter=args.hash_filename_filter)
    c.options["discover_hash_files_depth"] = args.discover_hash_files_depth
    c.move_files(args.source_path, args.mv_path)


def _cl_verify_all(args: argparse.Namespace) -> Tuple[int, int, int, int]:
    files_total = 0
    all_missing = []
    all_failed_checksums = []
    # verify all found hashes of discovered hash files for all supplied paths
    for root_p in args.root_dir:
        c = ChecksumHelper(root_p, hash_filename_filter=args.hash_filename_filter)
        c.options["discover_hash_files_depth"] = args.discover_hash_files_depth
        c.build_most_current()
        # hash_file_most_current can either be of type HashFile or MixedAlgoHashCollection
        crc_errors, missing, matches = cast(ChecksumHelperData,
                                            c.hash_file_most_current).verify()
        all_missing.append((root_p, missing))
        all_failed_checksums.append((root_p, crc_errors))
        files_total += len(
            cast(ChecksumHelperData,
                 c.hash_file_most_current).entries)

    print("\nVerified folders: %s" % (", ".join(args.root_dir),))
    _print_summary(files_total, all_missing, all_failed_checksums)

    nr_missing = sum(len(x[1]) for x in all_missing)
    nr_failed_checksums = sum(len(x[1]) for x in all_failed_checksums)
    return files_total, files_total - nr_missing - nr_failed_checksums, nr_missing, nr_failed_checksums


def _cl_verify_hfile(args: argparse.Namespace) -> Tuple[int, int, int, int]:
    files_total = 0
    all_missing = []
    all_failed_checksums = []
    for hash_file in args.hash_file_name:
        cshd = ChecksumHelperData(None, hash_file)
        cshd.read()
        crc_errors, missing, matches = cshd.verify()
        all_missing.append((cshd.root_dir, missing))
        all_failed_checksums.append((cshd.root_dir, crc_errors))

        files_total += len(cshd.entries)

    print("\nVerified hash files: %s" % (", ".join(args.hash_file_name),))
    _print_summary(files_total, all_missing, all_failed_checksums)

    nr_missing = sum(len(x[1]) for x in all_missing)
    nr_failed_checksums = sum(len(x[1]) for x in all_failed_checksums)
    return files_total, files_total - nr_missing - nr_failed_checksums, nr_missing, nr_failed_checksums


def _print_summary(files_total: int, missing: List[Tuple[str, List[str]]],
                   failed_checksums: List[Tuple[str, List[Tuple[str, str]]]]):

    nr_missing = sum(len(x[1]) for x in missing)
    nr_failed_checksums = sum(len(x[1]) for x in failed_checksums)

    if any(x[1] for x in missing):
        print("\nMISSING FILES:")
        for root, fnames in missing:
            if not fnames:
                continue
            print(f"\n    ROOT FOLDER: {root}{os.sep}\n    |--> ", end="")
            print(f"\n    |--> ".join(fnames))
    else:
        print("\nNO MISSING FILES!")

    if any(x[1] for x in failed_checksums):
        print("\nFAILED CHECKSUMS:")
        for root, failure_type_fnames in failed_checksums:
            if not failure_type_fnames:
                continue
            print(f"\n    ROOT FOLDER: {root}{os.sep}\n    |--> ", end="")
            print(f"\n    |--> ".join(f"{failure_type}: {fname}"
                  for failure_type, fname in failure_type_fnames))
    else:
        print("\nNO FAILED CHECKSUMS!")

    print("\nSUMMARY:")
    print("    TOTAL FILES:", files_total)
    print("    MATCHES:", files_total - nr_missing - nr_failed_checksums)
    print("    FAILED CHECKSUMS:", nr_failed_checksums)
    print("    MISSING:", nr_missing)


def _cl_verify_filter(args: argparse.Namespace) -> None:
    c = ChecksumHelper(args.root_dir, hash_filename_filter=args.hash_filename_filter)
    c.options["discover_hash_files_depth"] = args.discover_hash_files_depth
    c.build_most_current()
    # so windows users can use both /  and \ (unix doesn't have os.altsep)
    filter_unified = [x.replace(os.altsep, os.sep) for x in args.filter] if os.sep == '\\' else args.filter
    cast(ChecksumHelperData,
         c.hash_file_most_current).verify(whitelist=filter_unified)


class SmartFormatter(argparse.HelpFormatter):
    """Smart formatter that uses the RawTextFormatter if the help text begins with 'R|'
       src: https://stackoverflow.com/a/22157136 by Anthon"""

    def _split_lines(self, text: str, width: int) -> List[str]:
        if text.startswith('R|'):
            return text[2:].splitlines()  
        # this is the RawTextHelpFormatter._split_lines
        return argparse.HelpFormatter._split_lines(self, text, width)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Combine discovered checksum files into "
                                                 "one with the most current checksums or "
                                                 "build a new incremental checksum file "
                                                 "for the specified dir and all subdirs",
                                                 formatter_class=SmartFormatter)

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
                               help="R|Number of subdirs to descend down to search for hash files:\n"
                                    " 0 -> root dir only\n-1 -> max depth\nDefault: -1",
                               metavar="DEPTH")
    parent_parser.add_argument("-v", "--verbosity", action="count", default=0,
                               help="increase output verbosity")

    incremental = subparsers.add_parser("incremental", aliases=["inc"], parents=[parent_parser],
                                        help="Discover hash files in subdirectories and verify"
                                             " found hashes and creating new hashes for new "
                                             "files! (So not truly incremental). ATTENTION: Only "
                                             "__new__ hashes will be written to file use "
                                             "--include-unchagned to write all hashes!",
                                        formatter_class=SmartFormatter)
    incremental.add_argument("path", type=str)
    incremental.add_argument("hash_algorithm", type=str)
    incremental.add_argument("--dont-include-unchanged", action="store_true",
                             help="Don't include the checksum of unchanged files in the output")
    incremental.add_argument("-s", "--single-hash", action="store_true",
                             help="Force files to be written as single hash (*.sha512, *.md5, etc.) files. "
                                  "Does not support storing mtimes (default format is .cshd)!")
    incremental.add_argument("--skip-unchanged", action="store_true",
                             help="Skip generating and comparing hashes for files that have the same "
                                  "modification time as the file on record! (There are ways that a "
                                  "file can change without the mtime changing and like this "
                                  "the source is not checked for corruption!)")
    incremental.add_argument("--dont-collect-mtime", action="store_true",
                             help="Don't collect the modification time of files that would be used "
                                  "for the --skip-unchanged flag and for emitting warnings "
                                  "if a file should not have changed when doing an incremental checksum")
    incremental.add_argument("-o", "--out-filename", type=str,
                             help="Default filename is the the name of the parent dir with "
                                  "the date appended, by default a .cshd file is created. "
                                  "Specify a filename having a hash type "
                                  "(see hashlib.algorithms_available) as extension to have all "
                                  "other hashes be re-hashed to this one!")
    # only either white or blacklist can be used at the same time - not both
    inc_wl_or_bl = incremental.add_mutually_exclusive_group()
    inc_wl_or_bl.add_argument("-wl", "--whitelist", nargs="+", metavar='PATTERN', default=None,
                              help="R|Only file paths matching one of the wildcard patterns "
                                   "will be hashed\n"
                                   "* -> Matches 0 or more chars (including / and \\\n"
                                   "? -> Matches any one character (including / and \\)\n",
                                   type=str)
    inc_wl_or_bl.add_argument("-bl", "--blacklist", nargs="+", metavar='PATTERN', default=None,
                              help="Wildcard patterns matching file paths to exclude from hashing",
                              type=str)
    incremental.add_argument("--per-directory", action="store_true", default=False,
                             help="Create one hash file per __top-level__ directory")
    # set func to call when subcommand is used
    incremental.set_defaults(func=_cl_incremental)

    build_most_current = subparsers.add_parser("build-most-current", aliases=["build"],
                                               parents=[parent_parser],
                                               help="Discover hash files in subdirectories and "
                                                    "write the newest ones to file. ATTENTION: "
                                                    "removes hashes of missing files by default!")
    build_most_current.add_argument("path", type=str)
    build_most_current.add_argument("-o", "--out-filename", type=str,
                                    help="Default filename is the the name of the parent dir with "
                                         "_most_current_ and the date appended, if multiple hash "
                                         "types are used a .cshd file is created. Specify a filename "
                                         "having a hash type (see hashlib.algorithms_available) as "
                                         "extension to have all other hashes be re-hashed to this one!")
    # store_true -> default false, when specified true <-> store_false reversed
    build_most_current.add_argument("--dont-filter-deleted", action="store_true",
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

    copy_parser = subparsers.add_parser("copy_hf", aliases=["cphf"], parents=[parent_parser],
                                        help="Copy a hash file modifying the relative paths "
                                             "within accordingly so they are still valid.")
    copy_parser.add_argument("source_path", type=str,
                             help="Path to the hash file that should be copied")
    copy_parser.add_argument("dest_path", type=str,
                             help="Absolute or relative (to the source_path) path to the destination "
                                  "of copied hash file (paths not ending in \\ or / are assumed to "
                                  "be file paths!): e.g. C:\\test\\photos.sha512, C:\\test\\, "
                                  "../test/photos.sha512, .\\..\\test2\\")
    # set func to call when subcommand is used
    copy_parser.set_defaults(func=_cl_copy)

    move = subparsers.add_parser("move", aliases=["mv"], parents=[parent_parser],
                                 help="Move a (hash-)file/folder modifying the paths "
                                      "in hash files that were found in subdirs of the root_dir "
                                      "accordingly so they are still valid.")
    move.add_argument("root_dir", type=str,
                      help="Root directory where we look for hash files in subdirectories. "
                           "Make sure to choose this wisely since file paths of moved files "
                           "won't be modified in dirs above the root_dir!")
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
    verify_all = verify_subcmds.add_parser("all", aliases=(),
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

    verify_filter = verify_subcmds.add_parser("filter", aliases=('f',),
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

    if args.verbosity == 1:
        stdohandler.setLevel(LOG_LVL_VERBOSE)
    elif args.verbosity >= 2:
        stdohandler.setLevel(LOG_LVL_EXTRAVERBOSE)

    if hasattr(args, "whitelist") and os.sep == '\\':
        # so windows users can use both /  and \ (unix doesn't have os.altsep)
        args.whitelist = ([pat.replace(os.altsep, os.sep) for pat in args.whitelist]
                          if args.whitelist else None)
        args.blacklist = ([pat.replace(os.altsep, os.sep) for pat in args.blacklist]
                          if args.blacklist else None)
    
    args.func(args)
