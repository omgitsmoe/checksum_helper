# checksum-helper

Convenient tool that facilitates a lot of common checksum file operations.

Features:

- Generate checksums for a whole directory tree either verifying files based on checksum files in
  the tree or skipping unchanged files based on the last modification time
- Combine all found checksum files in a directory tree into one common checksum file while only
  using the most recent checksums and filtering deleted files (can be turned off)
- Check whether all files in a directory tree have checksums
- Copy a hash file modifying the relative paths in the file accordingly
- Move files modifying all relative paths in checksum files accordingly
- Verify operations:
    - Verify all hashes of a single file
    - Verify all checksums that were found in the directory tree
    - Verify files based on a wildcard filter

## Usage

Use `checksum_helper.py -h` to display a list of subcommands and how to use them.
Subcommands (short alias):
- incremental (inc)
- build-most-current (build)
- check-missing (check)
- copy\_hf (cphf)
- move (mv)
- verify (vf)

For almost all commands the directory tree is searched for known checksum files.
This can be customized by specifying exclusion patterns using `--hash-filename-filter [PATTERN ...]`
and the traversal depth can be limited with `-d DEPTH`.

ChecksumHelper has it's own format that also stores the last modification time as well as
the hash type. If you want to avoid a custom format you can specify a filename with
`-o OUT_FILENAME` which has to end in a hash name (based on hashlib's naming) as
extension. Single hash files won't support emitting extra warnings when doing
incremental checksums or skipping unchanged files based on the last modification
time though.

For the filter/whitelist/.. wildcard patterns:
- On POSIX platforms: only `/` can be used as path separator
- On Windows: both `/` and `\` can be used interchangeably


### incremental
```
checksum_helper incremental path hash_algorithm
```

Generate checksums for a whole directory tree starting at `path`. The tree is searched
for known checksum files (\*.md5, \*.sha512, etc.). When generating new checksums
the files are verified against the most recent checksum that was found.

`--skip-unchanged`: skip verifying files by hash if the the last modification time remains unchanged

`--dont-include-unchanged`: Unchanged files are included in the generated checksum
    file by default, this can be turned off by using this flag

`-s` or `--single-hash`: Force writing to a single hash file

### build-most-current
```
checksum_helper build path
```

Combine all found checksum files in a directory tree starting at `path` into
one common checksum file while only using the most recent checksums. By default
files that have been deleted in `path` will not be included which can be turned off
using `--dont-filter-deleted`.

### check-missing
```
checksum_helper check path
```

Check whether all files in a directory tree starting at `path` have checksums
available (in discovered checksum files)

### copy\_hf
```
checksum_helper cphf source_path dest_path
```
Copy a hash file at `source_path` to `dest_path` modifying the relative paths in
the file accordingly

### move
```
checksum_helper mv root_dir source_path mv_path
```

Move file(s) or a directory from `source_path` to `mv_path` modifying all relative
paths in checksum files, that were found in the directory tree starting at `root_dir`,
accordingly.

Make sure to be careful about choosing `root_dir` since relative paths to the moved
file(s) won't be modified in parent directories.

### verify

For all verify operations a summary containing the `FAILED`/`MISSING` files
and the amount of total files, matches, etc. are printed so you don't have to
go through all the logs manually.

Verify operations:

#### all
```
checksum_helper vf all root_dir
```

Verify all checksums that were found in the directory tree starting at `root_dir`

#### hash\_file
```
checksum_helper vf hf hash_file_name
```

Verify all hashes in a checksum file at `hash_file_name`.

#### filter
```
checksum_helper vf filter root_dir filter [filter ...]
```

Verify files based on mutiple wildcard filters such that only files matching
one of the filters is verified, assuming there is a hash in a checksum file
somewhere in `root_dir` for it.

Example:
```
checksum_helper vf filter phone_backup "*.jpg" "*.mp4" "Books/*"
```

This would verify all `jpg` and `mp4` files as well as all files in the
sub-directory `Books` (as long as there are checksums for it in `phone_backup`)
