#!/usr/bin/python
# coding: utf-8

# Contains functionality for unpacking EO MSG2 tables
#
# written by TheOnlyOne (@modest_ralts)

import argparse
from struct import unpack
import convert_EOstring
from sys import stderr

def eprint(s):
    stderr.write(s + "\n")

def parseArguments():
    # Create argument parser
    parser = argparse.ArgumentParser(description="Parses an Etrian Odyssey .mbm/MSG2 file.")

    # Positional mandatory arguments
    parser.add_argument("input_file", help="name of the file containing the raw name table data")
    parser.add_argument("output_file", help="name of the file in which to place the output")

    # Optional arguments
    parser.add_argument("--hide_pos", action="store_true", help="positions will not be displayed")
    parser.add_argument("--show_output", action="store_true", help="output will be printed to console in addition to being saved to the output_file")
    parser.add_argument("--hide_alerts", action="store_true", help="warnings will not be printed to stderr if unknown characters are encountered") 


    # Print version
    parser.add_argument("--version", action="version", version='%(prog)s - Version 1.0')

    # Parse arguments
    args = parser.parse_args()

    return args



# Data structure that stores the message table
# size is the number of elements in the table
# indices is the internal index given to the message
# sizes is the length of each message
# posisitions is an array of pointers to the start of the message in the file
# raw_names is an array of the raw EOstring names
# names is an array of readable names
class EO_MSG_table:

    # Populate the table using the raw data
    def build_from_data(self, data, alert_unk=False):

        # read the header of the file
        header = unpack("<2I4H4I", data[0:0x20])
        if alert_unk:
            if header[0] != 0:
                eprint("Unknown padding at byte 0x00: " + "{:#010x}".format(header[0]))
            if header[1] != 0x3247534D:
                eprint("MSG2 tag not found, it was: " + "{:#010x}".format(header[1]))
            if header[2] != 0:
                eprint("Unknown padding at byte 0x08: " + "{:#06x}".format(header[2]))
            if header[3] != 1:
                eprint("Unknown padding at byte 0x0A: " + "{:#06x}".format(header[3]))
            if header[5] != 0:
                eprint("Unknown padding at byte 0x0E: " + "{:#06x}".format(header[5]))
            if header[7] != 0x20:
                eprint("Unknown padding at byte 0x14: " + "{:#010x}".format(header[7]))
            if header[8] != 0:
                eprint("Unknown padding at byte 0x18: " + "{:#010x}".format(header[8]))
            if header[9] != 0:
                eprint("Unknown padding at byte 0x1B: " + "{:#010x}".format(header[9]))

        filesize = header[4]
        self.size = header[6]
  
        amount_found = 0
        cur_pos = 0x20
        while amount_found < self.size:
            subheader = unpack("<4I", data[cur_pos:cur_pos+0x10])
            cur_pos += 0x10
            if subheader[1] == 0:
                continue
            self.indices.append(subheader[0])
            self.sizes.append(subheader[1])
            self.positions.append(subheader[2])
            if subheader[3] != 0:
                eprint("Unknown padding at position " + "{:#010x}".format(cur_pos-0x10) + ": " + "{:#010x}".format(subheader[3]))
            amount_found += 1 

        # read the names
        # name table is after the position table
        for index in range(0, self.size):
            pos = self.positions[index]
            eostring = ""
            for char in range(self.sizes[index]):
                eostring += data[pos + char]
            self.raw_names.append(eostring)
            self.names.append( convert_EOstring.eostring_to_string(eostring, alert_unk) )


    # Popluate the table using a given file
    def build_from_file(self, tblfile, alert_unk):
        data = ""
        with open(tblfile) as f:
            data = f.read()
        self.build_from_data(data, alert_unk)


    # Create an empty name table
    def __init__(self):
        self.size = 0
        self.positions = []
        self.raw_names = []
        self.names = []
        self.indices = []
        self.sizes = []

if __name__ == '__main__':
    # Parse the arguments
    args = parseArguments()

    # Build the table from the given file
    tbl = EO_MSG_table()
    tbl.build_from_file(args.input_file,  not args.hide_alerts)

    # Construct the output
    lines = ["index\tmessage"]

    for index in range(0, tbl.size):
        row_data = [str(tbl.indices[index])]
        row_data.append( tbl.names[index].replace("\n", "\n\t") )
        lines += ["\t".join(row_data) + "\n"]
    output = "\n".join(lines)

    if args.show_output:
        print output

    # Write result to a file
    with open(args.output_file, "w") as f:
        f.write(output)
