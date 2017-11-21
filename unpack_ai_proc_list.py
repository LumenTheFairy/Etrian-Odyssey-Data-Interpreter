#!/usr/bin/python
# coding: utf-8

# Contains functionality for unpacking the lists of AI procedures
# which maps an entities AI index to the actual procedure name
#
# written by TheOnlyOne (@modest_ralts)

import argparse

def parseArguments():
    # Create argument parser
    parser = argparse.ArgumentParser(description="Parses an Etrian Odyssey procedure list.")

    # Positional mandatory arguments
    parser.add_argument("num_procs", type=int, help="the number of procedure names in the file")
    parser.add_argument("input_file", help="name of the file containing the raw procedure name list")
    parser.add_argument("output_file", help="name of the file in which to place the output") 

    # Optional arguments
    parser.add_argument("--show_output", action="store_true", help="output will be printed to console in addition to being saved to the output_file")

    # Print version
    parser.add_argument("--version", action="version", version='%(prog)s - Version 1.0')

    # Parse arguments
    args = parser.parse_args()

    return args

# the files are simply a list of 0x20 width strings with 0s filling the space
def get_procedure_names(filename, num_names):

    # read the file
    data = ""
    with open(filename) as f:
        data = f.read()

    # get the strings
    proc_names = []
    for idx in range(num_names):
        base = idx * 0x20
        if base >= len(data):
            break
        name = ""
        for c in data[base : base + 0x20]:
            if c == '\x00':
                break
            name += c
        proc_names.append(name)

    # pad the list if it was too short
    proc_names += [""] * ( num_names - len(proc_names) )

    return proc_names

def unpack_proc_main():

    # Parse the arguments
    args = parseArguments()

    # parse the procedure name file
    proc_names = get_procedure_names(args.input_file, args.num_procs)

    lines = ["index\tname"]
    for idx, name in enumerate(proc_names):
        lines.append( "\t".join([str(idx), name]) )
    output = "\n".join(lines)

    if args.show_output:
        print output

    # Write result to a file
    with open(args.output_file, "w") as f:
        f.write(output)

if __name__ == '__main__':
    unpack_proc_main()
