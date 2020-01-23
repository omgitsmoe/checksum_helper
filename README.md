# ChecksumHelper
ChecksumHelper is a tool for working with checksum files. It can for example generate incremental checksum files, 
move a hash file while keeping all paths intact 
or verify all files that it finds hashes for in checksum files that were discovered in a folder's sub-directories.

## Usage
Use `checksum_helper.py -h` to display a list of subcommands and how to use them.
Subcommands (short alias):
- incremental (inc)
- build-most-current (build)
- check-missing (check)
- copy (cp)
- move (mv)
- verify (vf)