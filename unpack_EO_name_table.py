#!/usr/bin/python
# coding: utf-8

# Contains functionality for unpacking EO name tables
# if run from the command line, will take a table file and unpack the name
# list into a given output file
#
# written by TheOnlyOne (@modest_ralts)

import argparse
from struct import unpack
import convert_EOstring
from shared_helpers import d

def parseArguments():
    # Create argument parser
    parser = argparse.ArgumentParser(description="Parses an Etrian Odyssey name table and places the result in an output tsv. End is the location of end of the raw string in the data table. This is largely irrelevant after the parsing is already done. Raw name shows the hex for the name. Name is the (English) readable name.")

    # Positional mandatory arguments
    parser.add_argument("input_file", help="name of the file containing the raw name table data")
    parser.add_argument("output_file", help="name of the file in which to place the output") 

    # Optional arguments
    parser.add_argument("--index_width", type=int, choices=[2,4], default=2, help="width, in bytes, of the indexes at the start of the table")
    parser.add_argument("--hide_pos", action="store_true", help="positions will not be displayed")
    parser.add_argument("--hide_raw", action="store_true", help="raw names will not be displayed")
    parser.add_argument("--show_output", action="store_true", help="output will be printed to console in addition to being saved to the output_file")
    parser.add_argument("--hide_alerts", action="store_true", help="warnings will not be printed to stderr if unknown characters are encountered") 


    # Print version
    parser.add_argument("--version", action="version", version='%(prog)s - Version 1.0')

    # Parse arguments
    args = parser.parse_args()

    return args



# Data structure that stores the name table
# size is the number of elements in the table
# posisitions is an array of size indexes that gives the end location of the respective name
#     thus, the last position points to the end of the table
# raw_names is an array of the raw EOstring names
# names is an array of readable names
class EO_name_table:

    # Populate the table using given raw data
    def build_from_data(self, data, width, alert_unk=False):
        # grabs the correctly-widthed starting at index i
        def data_slice(i):
            return data[i : i+width]
        # converts raw string into an int
        def data_val(value):
            if width == 2:
                return unpack("<H", value)[0]
            if width == 4:
                return unpack("<I", value)[0]

        # read the size of the table
        self.size = data_val(data_slice(0))

        # read the index list
        # position table is after the size
        position_table_base = width
        for index in range(0, self.size):
            self.positions.append( data_val(data_slice(width*index + position_table_base)) )

        data = d(data)

        # read the names
        # name table is after the position table
        name_table_base = width * (self.size + 1)
        for index in range(0, self.size):
            pos = name_table_base
            if index > 0:
                pos += self.positions[index - 1]
            eostring = ""
            while data[pos] != '\x00':
                eostring += data[pos]
                pos += 1
            self.raw_names.append(eostring)
            self.names.append( convert_EOstring.eostring_to_string(eostring, alert_unk) )


    # Popluate the table using a given file
    def build_from_file(self, tblfile, width, alert_unk):
        data = ""
        with open(tblfile, "rb") as f:
            data = f.read()
        self.build_from_data(data, width, alert_unk)


    # Create an empty name table
    def __init__(self):
        self.size = 0
        self.positions = []
        self.raw_names = []
        self.names = []



if __name__ == '__main__':
    # Parse the arguments
    args = parseArguments()

    # Build the table from the given file
    tbl = EO_name_table()
    tbl.build_from_file(args.input_file, args.index_width, not args.hide_alerts)

    # Construct the output
    header = ["index"]
    if not args.hide_pos:
        header.append( "end" )
    if not args.hide_raw:
        header.append( "raw name" )
    header.append( "name" )
    output = "\t".join(header) + "\n"

    for index in range(0, tbl.size):
        row_data = [str(index)]
        if not args.hide_pos:
            row_data.append( str(tbl.positions[index]) )
        if not args.hide_raw:
            row_data.append( convert_EOstring.display_eostring(tbl.raw_names[index]) )
        row_data.append( tbl.names[index] )
        output += "\t".join(row_data) + "\n"

    if args.show_output:
        print(output)

    # Write result to a file
    with open(args.output_file, "w") as f:
        f.write(output)
