# apdapted from: http://developforperformance.com/MatchingWildcards_AnImprovedAlgorithmForBigData.html
# Original by Kirk J Krauss
# Copyright 2018 IBM Corporation
# 
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
# 
#     http://www.apache.org/licenses/LICENSE-2.0
# 
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
from checksum_helper import wildcard_match


def wildcard_caller(text, pattern, expected):
    # wildcard_match(pattern, text)
    # use is here to make sure we acutally get True not a value that just evaluates to True
    assert wildcard_match(pattern, text) is expected


def test_wildcard_matching():
    # Case with first wildcard after total match.
    wildcard_caller("Hi", "Hi*", True)

    # Case with mismatch after '*'
    wildcard_caller("abc", "ab*d", False)

    # Cases with repeating character sequences.
    wildcard_caller("abcccd", "*ccd", True)
    wildcard_caller("mississipissippi", "*issip*ss*", True)
    wildcard_caller("xxxx*zzzzzzzzy*f", "xxxx*zzy*fffff", False)
    wildcard_caller("xxxx*zzzzzzzzy*f", "xxx*zzy*f", True)
    wildcard_caller("xxxxzzzzzzzzyf", "xxxx*zzy*fffff", False)
    wildcard_caller("xxxxzzzzzzzzyf", "xxxx*zzy*f", True)
    wildcard_caller("xyxyxyzyxyz", "xy*z*xyz", True)
    wildcard_caller("mississippi", "*sip*", True)
    wildcard_caller("xyxyxyxyz", "xy*xyz", True)
    wildcard_caller("mississippi", "mi*sip*", True)
    wildcard_caller("ababac", "*abac*", True)
    wildcard_caller("ababac", "*abac*", True)
    wildcard_caller("aaazz", "a*zz*", True)
    wildcard_caller("a12b12", "*12*23", False)
    wildcard_caller("a12b12", "a12b", False)
    wildcard_caller("a12b12", "*12*12*", True)

    # From DDJ reader Andy Belf
    wildcard_caller("caaab", "*a?b", True)

    # Additional cases where the '*' char appears in the tame string.
    wildcard_caller("*", "*", True)
    wildcard_caller("a*abab", "a*b", True)
    wildcard_caller("a*r", "a*", True)
    wildcard_caller("a*ar", "a*aar", False)

    # More double wildcard scenarios.
    wildcard_caller("XYXYXYZYXYz", "XY*Z*XYz", True)
    wildcard_caller("missisSIPpi", "*SIP*", True)
    wildcard_caller("mississipPI", "*issip*PI", True)
    wildcard_caller("xyxyxyxyz", "xy*xyz", True)
    wildcard_caller("miSsissippi", "mi*sip*", True)
    wildcard_caller("miSsissippi", "mi*Sip*", False)
    wildcard_caller("abAbac", "*Abac*", True)
    wildcard_caller("abAbac", "*Abac*", True)
    wildcard_caller("aAazz", "a*zz*", True)
    wildcard_caller("A12b12", "*12*23", False)
    wildcard_caller("a12B12", "*12*12*", True)
    wildcard_caller("oWn", "*oWn*", True)

    # Completely tame (no wildcards) cases.
    wildcard_caller("bLah", "bLah", True)
    wildcard_caller("bLah", "bLaH", False)

    # Simple mixed wildcard tests suggested by Marlin Deckert.
    wildcard_caller("a", "*?", True)
    wildcard_caller("ab", "*?", True)
    wildcard_caller("abc", "*?", True)

    # More mixed wildcard tests including coverage for false positives.
    wildcard_caller("a", "??", False)
    wildcard_caller("ab", "?*?", True)
    wildcard_caller("ab", "*?*?*", True)
    wildcard_caller("abc", "?**?*?", True)
    wildcard_caller("abc", "?**?*&?", False)
    wildcard_caller("abcd", "?b*??", True)
    wildcard_caller("abcd", "?a*??", False)
    wildcard_caller("abcd", "?**?c?", True)
    wildcard_caller("abcd", "?**?d?", False)
    wildcard_caller("abcde", "?*b*?*d*?", True)

    # Single-character-match cases.
    wildcard_caller("bLah", "bL?h", True)
    wildcard_caller("bLaaa", "bLa?", False)
    wildcard_caller("bLah", "bLa?", True)
    wildcard_caller("bLaH", "?Lah", False)
    wildcard_caller("bLaH", "?LaH", True)

    # Many-wildcard scenarios.
    wildcard_caller("aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa\
aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaab", 
        "a*a*a*a*a*a*aa*aaa*a*a*b", True)
    wildcard_caller("abababababababababababababababababababaacacacacaca\
cacadaeafagahaiajakalaaaaaaaaaaaaaaaaaffafagaagggagaaaaaaaab", 
        "*a*b*ba*ca*a*aa*aaa*fa*ga*b*", True)
    wildcard_caller("abababababababababababababababababababaacacacacaca\
cacadaeafagahaiajakalaaaaaaaaaaaaaaaaaffafagaagggagaaaaaaaab", 
        "*a*b*ba*ca*a*x*aaa*fa*ga*b*", False)
    wildcard_caller("abababababababababababababababababababaacacacacaca\
cacadaeafagahaiajakalaaaaaaaaaaaaaaaaaffafagaagggagaaaaaaaab", 
        "*a*b*ba*ca*aaaa*fa*ga*gggg*b*", False)
    wildcard_caller("abababababababababababababababababababaacacacacaca\
cacadaeafagahaiajakalaaaaaaaaaaaaaaaaaffafagaagggagaaaaaaaab", 
        "*a*b*ba*ca*aaaa*fa*ga*ggg*b*", True)
    wildcard_caller("aaabbaabbaab", "*aabbaa*a*", True)
    wildcard_caller("a*a*a*a*a*a*a*a*a*a*a*a*a*a*a*a*a*", 
        "a*a*a*a*a*a*a*a*a*a*a*a*a*a*a*a*a*", True)
    wildcard_caller("aaaaaaaaaaaaaaaaa", 
        "*a*a*a*a*a*a*a*a*a*a*a*a*a*a*a*a*a*", True)
    wildcard_caller("aaaaaaaaaaaaaaaa", 
        "*a*a*a*a*a*a*a*a*a*a*a*a*a*a*a*a*a*", False)
    wildcard_caller("abc*abcd*abcde*abcdef*abcdefg*abcdefgh*abcdefghi*a\
bcdefghij*abcdefghijk*abcdefghijkl*abcdefghijklm*abcdefghijklmn", 
        "abc*abc*abc*abc*abc*abc*abc*abc*abc*abc*abc*abc*abc*abc*abc*abc*a\
        bc*", False)
    wildcard_caller("abc*abcd*abcde*abcdef*abcdefg*abcdefgh*abcdefghi*a\
bcdefghij*abcdefghijk*abcdefghijkl*abcdefghijklm*abcdefghijklmn", 
        "abc*abc*abc*abc*abc*abc*abc*abc*abc*abc*abc*abc*", True)
    wildcard_caller("abc*abcd*abcd*abc*abcd", "abc*abc*abc*abc*abc", 
        False)
    wildcard_caller(
        "abc*abcd*abcd*abc*abcd*abcd*abc*abcd*abc*abc*abcd", 
        "abc*abc*abc*abc*abc*abc*abc*abc*abc*abc*abcd", True)
    wildcard_caller("abc", "********a********b********c********", 
        True)
    wildcard_caller("********a********b********c********", "abc", 
        False)
    wildcard_caller("abc", "********a********b********b********", 
        False)
    wildcard_caller("*abc*", "***a*b*c***", True)

    # A case-insensitive algorithm test.
    # wildcard_caller("mississippi", "*issip*PI", True)

    # Tests suggested by other DDJ readers
    wildcard_caller("", "?", False)
    wildcard_caller("", "*?", False)
    wildcard_caller("", "", True)
    wildcard_caller("a", "", False)

    # Case with last character mismatch.
    wildcard_caller("abc", "abd", False)

    # Cases with repeating character sequences.
    wildcard_caller("abcccd", "abcccd", True)
    wildcard_caller("mississipissippi", "mississipissippi", True)
    wildcard_caller("xxxxzzzzzzzzyf", "xxxxzzzzzzzzyfffff", False)
    wildcard_caller("xxxxzzzzzzzzyf", "xxxxzzzzzzzzyf", True)
    wildcard_caller("xxxxzzzzzzzzyf", "xxxxzzy.fffff", False)
    wildcard_caller("xxxxzzzzzzzzyf", "xxxxzzzzzzzzyf", True)
    wildcard_caller("xyxyxyzyxyz", "xyxyxyzyxyz", True)
    wildcard_caller("mississippi", "mississippi", True)
    wildcard_caller("xyxyxyxyz", "xyxyxyxyz", True)
    wildcard_caller("m ississippi", "m ississippi", True)
    wildcard_caller("ababac", "ababac?", False)
    wildcard_caller("dababac", "ababac", False)
    wildcard_caller("aaazz", "aaazz", True)
    wildcard_caller("a12b12", "1212", False)
    wildcard_caller("a12b12", "a12b", False)
    wildcard_caller("a12b12", "a12b12", True)

    # A mix of cases
    wildcard_caller("n", "n", True)
    wildcard_caller("aabab", "aabab", True)
    wildcard_caller("ar", "ar", True)
    wildcard_caller("aar", "aaar", False)
    wildcard_caller("XYXYXYZYXYz", "XYXYXYZYXYz", True)
    wildcard_caller("missisSIPpi", "missisSIPpi", True)
    wildcard_caller("mississipPI", "mississipPI", True)
    wildcard_caller("xyxyxyxyz", "xyxyxyxyz", True)
    wildcard_caller("miSsissippi", "miSsissippi", True)
    wildcard_caller("miSsissippi", "miSsisSippi", False)
    wildcard_caller("abAbac", "abAbac", True)
    wildcard_caller("abAbac", "abAbac", True)
    wildcard_caller("aAazz", "aAazz", True)
    wildcard_caller("A12b12", "A12b123", False)
    wildcard_caller("a12B12", "a12B12", True)
    wildcard_caller("oWn", "oWn", True)
    wildcard_caller("bLah", "bLah", True)
    wildcard_caller("bLah", "bLaH", False)

    # Single '?' cases.
    wildcard_caller("a", "a", True)
    wildcard_caller("ab", "a?", True)
    wildcard_caller("abc", "ab?", True)

    # Mixed '?' cases.
    wildcard_caller("a", "??", False)
    wildcard_caller("ab", "??", True)
    wildcard_caller("abc", "???", True)
    wildcard_caller("abcd", "????", True)
    wildcard_caller("abc", "????", False)
    wildcard_caller("abcd", "?b??", True)
    wildcard_caller("abcd", "?a??", False)
    wildcard_caller("abcd", "??c?", True)
    wildcard_caller("abcd", "??d?", False)
    wildcard_caller("abcde", "?b?d*?", True)

    # Longer string scenarios.
    wildcard_caller("aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa\
aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaab", 
        "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa\
aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaab", True)
    wildcard_caller("abababababababababababababababababababaacacacacaca\
cacadaeafagahaiajakalaaaaaaaaaaaaaaaaaffafagaagggagaaaaaaaab", 
        "abababababababababababababababababababaacacacacaca\
cacadaeafagahaiajakalaaaaaaaaaaaaaaaaaffafagaagggagaaaaaaaab", True)
    wildcard_caller("abababababababababababababababababababaacacacacaca\
cacadaeafagahaiajakalaaaaaaaaaaaaaaaaaffafagaagggagaaaaaaaab", 
        "abababababababababababababababababababaacacacacaca\
cacadaeafagahaiajaxalaaaaaaaaaaaaaaaaaffafagaagggagaaaaaaaab", False)
    wildcard_caller("abababababababababababababababababababaacacacacaca\
cacadaeafagahaiajakalaaaaaaaaaaaaaaaaaffafagaagggagaaaaaaaab", 
        "abababababababababababababababababababaacacacacaca\
cacadaeafagahaiajakalaaaaaaaaaaaaaaaaaffafagaggggagaaaaaaaab", False)
    wildcard_caller("abababababababababababababababababababaacacacacaca\
cacadaeafagahaiajakalaaaaaaaaaaaaaaaaaffafagaagggagaaaaaaaab", 
        "abababababababababababababababababababaacacacacaca\
cacadaeafagahaiajakalaaaaaaaaaaaaaaaaaffafagaagggagaaaaaaaab", True)
    wildcard_caller("aaabbaabbaab", "aaabbaabbaab", True)
    wildcard_caller("aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa", 
        "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa", True)
    wildcard_caller("aaaaaaaaaaaaaaaaa", 
        "aaaaaaaaaaaaaaaaa", True)
    wildcard_caller("aaaaaaaaaaaaaaaa", 
        "aaaaaaaaaaaaaaaaa", False)
    wildcard_caller("abcabcdabcdeabcdefabcdefgabcdefghabcdefghia\
bcdefghijabcdefghijkabcdefghijklabcdefghijklmabcdefghijklmn", 
        "abcabcabcabcabcabcabcabcabcabcabcabcabcabcabcabcabc", 
        False)
    wildcard_caller("abcabcdabcdeabcdefabcdefgabcdefghabcdefghia\
bcdefghijabcdefghijkabcdefghijklabcdefghijklmabcdefghijklmn", 
        "abcabcdabcdeabcdefabcdefgabcdefghabcdefghia\
bcdefghijabcdefghijkabcdefghijklabcdefghijklmabcdefghijklmn", 
        True)
    wildcard_caller("abcabcdabcdabcabcd", "abcabc?abcabcabc", 
        False)
    wildcard_caller(
        "abcabcdabcdabcabcdabcdabcabcdabcabcabcd", 
        "abcabc?abc?abcabc?abc?abc?bc?abc?bc?bcd", True)
    wildcard_caller("?abc?", "?abc?", True)

    # A simple case
    wildcard_caller("", "abd", False)

    # Cases with repeating character sequences
    wildcard_caller("", "abcccd", False)
    wildcard_caller("", "mississipissippi", False)
    wildcard_caller("", "xxxxzzzzzzzzyfffff", False)
    wildcard_caller("", "xxxxzzzzzzzzyf", False)
    wildcard_caller("", "xxxxzzy.fffff", False)
    wildcard_caller("", "xxxxzzzzzzzzyf", False)
    wildcard_caller("", "xyxyxyzyxyz", False)
    wildcard_caller("", "mississippi", False)
    wildcard_caller("", "xyxyxyxyz", False)
    wildcard_caller("", "m ississippi", False)
    wildcard_caller("", "ababac*", False)
    wildcard_caller("", "ababac", False)
    wildcard_caller("", "aaazz", False)
    wildcard_caller("", "1212", False)
    wildcard_caller("", "a12b", False)
    wildcard_caller("", "a12b12", False)

    # A mix of cases
    wildcard_caller("", "n", False)
    wildcard_caller("", "aabab", False)
    wildcard_caller("", "ar", False)
    wildcard_caller("", "aaar", False)
    wildcard_caller("", "XYXYXYZYXYz", False)
    wildcard_caller("", "missisSIPpi", False)
    wildcard_caller("", "mississipPI", False)
    wildcard_caller("", "xyxyxyxyz", False)
    wildcard_caller("", "miSsissippi", False)
    wildcard_caller("", "miSsisSippi", False)
    wildcard_caller("", "abAbac", False)
    wildcard_caller("", "abAbac", False)
    wildcard_caller("", "aAazz", False)
    wildcard_caller("", "A12b123", False)
    wildcard_caller("", "a12B12", False)
    wildcard_caller("", "oWn", False)
    wildcard_caller("", "bLah", False)
    wildcard_caller("", "bLaH", False)

    # Both strings empty
    wildcard_caller("", "", True)

    # Another simple case
    wildcard_caller("abc", "", False)

    # Cases with repeating character sequences.
    wildcard_caller("abcccd", "", False)
    wildcard_caller("mississipissippi", "", False)
    wildcard_caller("xxxxzzzzzzzzyf", "", False)
    wildcard_caller("xxxxzzzzzzzzyf", "", False)
    wildcard_caller("xxxxzzzzzzzzyf", "", False)
    wildcard_caller("xxxxzzzzzzzzyf", "", False)
    wildcard_caller("xyxyxyzyxyz", "", False)
    wildcard_caller("mississippi", "", False)
    wildcard_caller("xyxyxyxyz", "", False)
    wildcard_caller("m ississippi", "", False)
    wildcard_caller("ababac", "", False)
    wildcard_caller("dababac", "", False)
    wildcard_caller("aaazz", "", False)
    wildcard_caller("a12b12", "", False)
    wildcard_caller("a12b12", "", False)
    wildcard_caller("a12b12", "", False)

    # A mix of cases
    wildcard_caller("n", "", False)
    wildcard_caller("aabab", "", False)
    wildcard_caller("ar", "", False)
    wildcard_caller("aar", "", False)
    wildcard_caller("XYXYXYZYXYz", "", False)
    wildcard_caller("missisSIPpi", "", False)
    wildcard_caller("mississipPI", "", False)
    wildcard_caller("xyxyxyxyz", "", False)
    wildcard_caller("miSsissippi", "", False)
    wildcard_caller("miSsissippi", "", False)
    wildcard_caller("abAbac", "", False)
    wildcard_caller("abAbac", "", False)
    wildcard_caller("aAazz", "", False)
    wildcard_caller("A12b12", "", False)
    wildcard_caller("a12B12", "", False)
    wildcard_caller("oWn", "", False)
    wildcard_caller("bLah", "", False)
    wildcard_caller("bLah", "", False)


def wildcard_caller_partial(text, pattern, expected):
    # wildcard_match(pattern, text)
    # use is here to make sure we acutally get True not a value that just evaluates to True
    assert wildcard_match(pattern, text, partial_match=True) is expected


def test_wildcard_matching_partial():
    # Case with first wildcard after total match.
    wildcard_caller_partial("foo/", "foo*.txt", True)
    wildcard_caller_partial("foo/test.txt", "foo*.txt", True)
    wildcard_caller_partial("foo/test.txt", "*", True)
    wildcard_caller_partial("foo", "*", True)
    wildcard_caller_partial("foo/bar/", "fo?/*", True)

    wildcard_caller_partial("f_o/bar/", "fo?/*", False)
    wildcard_caller_partial("foo/bar/", "foo/qux/*", False)
    wildcard_caller_partial("foo/Qux/", "foo/qux/*", False)
