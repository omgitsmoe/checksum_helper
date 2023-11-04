import os
import sys
import glob
sys.path.insert(0, os.path.abspath('..'))

from checksum_helper import gen_hash_from_file, HASH_FILE_EXTENSIONS

def replace_in_all_hashfiles(literal, replacement):
    for dirpath, dirnames, fnames in os.walk('.'):
        for fn in fnames:
            try:
                ext = fn.rsplit(".", 1)[1]
            except IndexError:
                continue
            if ext not in HASH_FILE_EXTENSIONS:
                continue

            fpath = os.path.join(dirpath, fn)
            encoding = 'utf-8' if ext == "cshd" else 'utf-8-sig'
            with open(fpath, 'r', encoding=encoding) as f:
                current_content = f.read()

            if literal in current_content:
                # replace backslashes and windows line endings
                new_content = current_content.replace(literal, replacement)
                # print(f"REPL '{literal}' WITH '{replacement}'", "BERFORE REPL:\n", current_content, "\nAFTER REPL:\n", new_content)
                with open(fpath, 'w', encoding=encoding, newline='') as f:
                    f.write(new_content)


# for dirpath, dirnames, fnames in os.walk('.'):
#     for fn in fnames:
#         try:
#             ext = fn.rsplit(".", 1)[1]
#         except IndexError:
#             continue
#         if ext not in HASH_FILE_EXTENSIONS:
#             continue

#         fpath = os.path.join(dirpath, fn)
for fpath in glob.iglob("test*\\**\\*.*", recursive=True):
    print("CURR FILE:", fpath)
    ext = fpath.rsplit(".", 1)[1]
    # hash_type = ext if ext != "cshd" else "sha512"
    # current_hash = gen_hash_from_file(fpath, hash_type, True)
    current_hash_sha512 = gen_hash_from_file(fpath, "sha512", True)
    current_hash_md5 = gen_hash_from_file(fpath, "md5", True)

    encoding = 'utf-8' if ext == "cshd" else 'utf-8-sig'
    with open(fpath, 'r', encoding=encoding, newline='') as f:
        current_content = f.read()

    # replace backslashes and windows line endings
    # .replace("\\", "/")
    new_content = current_content.replace("\r\n", "\n")

    # print("BERFORE FIX:\n", current_content, "\nAFTER FIX:\n", new_content)


    # newline controls how universal newlines mode works (it only applies
    # to text mode). It can be None, '', '\n', '\r', and '\r\n'. It works
    # as follows:

    # When reading input from the stream, if newline is None, universal
    # newlines mode is enabled. Lines in the input can end in '\n', '\r',
    # or '\r\n', and these are translated into '\n' before being returned
    # to the caller. If it is '', universal newlines mode is enabled, but
    # line endings are returned to the caller untranslated. If it has any
    # of the other legal values, input lines are only terminated by the
    # given string, and the line ending is returned to the caller
    # untranslated.

    # When writing output to the stream, if newline is None, any '\n'
    # characters written are translated to the system default line
    # separator, os.linesep. If newline is '' or '\n', no translation takes
    # place. If newline is any of the other legal values, any '\n'
    # characters written are translated to the given string.
    if current_content != new_content:
        with open(fpath, 'w', encoding=encoding, newline='') as f:
            f.write(new_content)

        new_hash_sha512 = gen_hash_from_file(fpath, "sha512", True)
        new_hash_md5 = gen_hash_from_file(fpath, "md5", True)
        # new_hash = gen_hash_from_file(fpath, hash_type, True)
        # if current_hash != new_hash:
        #     print("HASH CHANGED")
        #     replace_in_all_hashfiles(current_hash, new_hash)

        replace_in_all_hashfiles(current_hash_sha512, new_hash_sha512)
        replace_in_all_hashfiles(current_hash_md5, new_hash_md5)

