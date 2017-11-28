# coding: utf-8

# Contains functions for converting between a string and an EOstring
#
# written by TheOnlyOne (@modest_ralts)

from struct import pack, unpack
from sys import stderr

# lookup table for special chars
special_chars = {
    '\x80\x01' : '\n',
    '\x80\x02' : '[Continue]',
    '\x81\x40' : ' ',
    '\x81\x43' : ',',
    '\x81\x44' : '.',
    '\x81\x45' : "'",
    '\x81\x46' : ':',
    '\x81\x47' : ';',
    '\x81\x48' : '?',
    '\x81\x49' : '!',
    '\x81\x5E' : '/',
    '\x81\x60' : '~',
    '\x81\x66' : "’",
    '\x81\x68' : "'",
    '\x81\x69' : '(',
    '\x81\x6A' : ')',
    '\x81\x6D' : '[',
    '\x81\x6E' : ']',
    '\x81\x7B' : '+',
    '\x81\x7C' : '-',
    '\x81\xA8' : '→',
    '\x81\xAA' : '↑',
    '\x81\xAB' : '↓',
    '\xff\xff' : '[End]',
}

# create a reversed lookup table
# TODO: double check the behavior of the duplicate use of '
reverse_special_chars = dict( [(v,k) for (k,v) in special_chars.items()] )

# converts an EOstring into a string that displays its hex
def display_eostring(eostring):
    return ''.join("{:02x}".format(ord(c)) for c in eostring)

# convert a single EOchar into a single char
# (the char will be returned in a string since some characters are variables)
# eochar must be a two character string
# alert_unk should be true to print a message when an unknown character is encountered
def eochar_to_char(eochar, alert_unk=False):

    # this is a letter or number
    if eochar[0] == '\x82':
        c = ord(eochar[1])
        # numbers
        if 0x4F <= c <= 0x58:
            return chr(c - 0x4F + ord('0'))
        #upper case
        elif 0x60 <= c <= 0x79:
            return chr(c - 0x60 + ord('A'))
        #lower case
        elif 0x81 <= c <= 0x9A:
            return chr(c - 0x81 + ord('a'))

    # color code
    if eochar == '\x80\x04':
      return "[Color]"
    # stored number lookup
    if eochar == '\x80\x10':
      return "[Number Display]"
    # item code
    if eochar == '\x80\x41':
      return "[Item]"
    # enemy code
    if eochar == '\x80\x42':
      return "[Enemy]"
    # enemy code
    if eochar == '\x80\x43':
      return "[Party Member]"
    #TODO: variable insertion, other string codes

    # this could be a special character
    if eochar in special_chars:
        return special_chars[eochar]

    # otherwise, the character is unkown
    if alert_unk:
        stderr.write("Could not convert EOchar: " + display_eostring(eochar) + "\n")
    return '<' + display_eostring(eochar) + '>'

# convert a single char into an EOchar
# (the EOchar will be returned as a string since it is multiple bytes)
# unknown chars will be replaced with a ?
# note that the special <####> format output for unknown chars in the other direction will NOT be converted back
# alert_unk should be true to print a message when an unknown is replaced
def char_to_eochar(c, alert_unk=False):
    
    n = ord(c)
    # numbers
    if ord('0') <= n <= ord('9'):
        return '\x82' + chr(n + 0x4F - ord('0'))
    #upper case
    elif ord('A') <= n <= ord('Z'):
        return '\x82' + chr(n + 0x60 - ord('A'))
    #lower case
    elif ord('a') <= n <= ord('z'):
        return '\x82' + chr(n + 0x81 - ord('a'))

    #TODO: color codes, variable insertion, other string codes

    # this could be a special character
    if c in reverse_special_chars:
        return reverse_special_chars[c]

    # otherwise, the character is unkown
    if alert_unk:
        stderr.write("Could not convert char: " + c + "\n")
    return reverse_special_chars['?']

# convert a full EOstring into a readable string
# eostring must have even length (it should not be null terminated)
# alert_unk should be true to print a message when an unknown character is encountered
def eostring_to_string(eostring, alert_unk=False):

    result = ""

    # loop through the string and build up the result
    i = 0
    while i < len(eostring)/2:
        eochar = eostring[2*i : 2*i+2]
        c = eochar_to_char(eochar, alert_unk)
        # special characters
        if c in ["[Color]", "[Item]", "[Enemy]", "[Number Display]", "[Party Member]"]:
            i += 1
            code = eostring[2*i : 2*i+2]
            c = c[:-1] + " " + str( unpack("<H", code.encode())[0] ) + "]"
        result += c
        i += 1

    return result

# convert a full string into an EOstring
# the returned string will not be null terminated
# alert_unk should be true to print a message when an unknown character is encountered
def string_to_eostring(s, alert_unk=False):

    result = ""

    # loop through the string and build up the result
    for c in s:
        result += char_to_eochar(c, alert_unk)

    return result
