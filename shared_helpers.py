# Contains functions that didn't really fit elsewhere, but are needed in multiple places
#
# written by TheOnlyOne (@modest_ralts)

# Convert an arbitrary width int-like into a list of bools, corresponding to the bits in the int-like
def int_like_to_flag_list(i, width):
    result = []
    for pos in range(0, width):
        result.append( 0 != (i & (1 << pos)) )
    return result

# Convert a char into a list of 8 bools, corresponding to the bits in the char
def char_to_flag_list(c):
    return int_like_to_flag_list(c, 8)

# Convert a list of chars into a list of bools, one for each bit of each char
def char_list_to_flag_list(cs):
    return [flag for flaglist in map(char_to_flag_list, cs) for flag in flaglist]

# Convert a string into a list of bools, one for each bit of the string
def string_to_flag_list(s):
    return char_list_to_flag_list( map(ord, s) )


# Flattens a list of lists
# https://stackoverflow.com/questions/952914/making-a-flat-list-out-of-list-of-lists-in-python
def flatten(l):
    return [item for sublist in l for item in sublist]

# used to wrap a file read so that it works in python 2 and 3
import sys
if sys.version_info < (3,):
    def d(x):
        return x
else:
    def d(x):
        return "".join(map(chr, x))
