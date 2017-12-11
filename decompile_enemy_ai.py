#!/usr/bin/python
# coding: utf-8

# Decompiles an enemy AI file, naming, to the extent possible, skills
# and enemies refered to in the AI script
# Uses the name tables:
#  game_name/Enemy/enemynametable.tbl
#  game_name/Skill/enemyskillnametable.tbl
# to fill in these names.
#
# written by TheOnlyOne (@modest_ralts)

import argparse
from sys import stderr
import os
import eo_value_lookup
import unpack_EO_name_table
import unpack_ai_proc_list
import unpack_ai
import decompile_ai

def parseArguments():
    # Create argument parser
    parser = argparse.ArgumentParser(description="Decompiles a single enemy AI file, naming skills and entities to the extent possible.")

    # Positional mandatory arguments
    parser.add_argument("game", choices=eo_value_lookup.game_codes, help="which game the data is from")
    parser.add_argument("input_file", help="name of the file containing the raw flw0 data")
    parser.add_argument("output_file", help="name of the file in which to place the output")

    parser.add_argument("--show_output", action="store_true", help="output will be printed to console in addition to being saved to the output_file")
    parser.add_argument("--fully_optimize", action="store_true", help="all optimization passes will be performed on the code; specific optimization flags will be ignored")
    parser.add_argument("--flatten_conditionals", action="store_true", help="(if . else if . else .) will be converted to (if . elif . else.) when permissable to reduce the nesting depth and resulting indentation of code")
    parser.add_argument("--flatten_elses", action="store_true", help="(if t return else f ) will be converted to (if t return f) when permissable to reduce the nesting depth and resulting indentation of code")
    parser.add_argument("--constant_folding", action="store_true", help="any arithmetic containing only constants will be replaced with the value of that expression")
    parser.add_argument("--simplify_conditions", action="store_true", help="boolean conditions will be simplified when it is permissable; see docs/ai_notes.txt for some warnings about this flag")
    parser.add_argument("--handwritten", action="store_true", help="use this for handwritten scripts if they don't seem to decompile well without it; see docs/ai_notes.txt for more details")

    # Print version
    parser.add_argument("--version", action="version", version='%(prog)s - Version 1.0')

    # Parse arguments
    args = parser.parse_args()

    return args

if __name__ == '__main__':
    # Parse the arguments
    args = parseArguments()

    # Build the enemy name table
    scr_names = unpack_EO_name_table.EO_name_table()
    scr_names.build_from_file(args.game + "/Enemy/enemynametable.tbl", 2, False)
    # Build the enemy skill name table
    scr_skill_names = unpack_EO_name_table.EO_name_table()
    scr_skill_names.build_from_file(args.game + "/Skill/enemyskillnametable.tbl", 2, False)
    # Build the decompilation
    decompile_ai.set_game_specific_values(args.game)
    flow = unpack_ai.Flow_File(args.input_file)
    basic_blocks, proc_info, special_labels = decompile_ai.abstract_flow(flow)
    abst = decompile_ai.ABST(basic_blocks, proc_info, special_labels, args.handwritten)
    if args.fully_optimize:
        abst.optimize_abst()
    else:
        abst.optimize_abst(args.flatten_conditionals, args.flatten_elses, args.constant_folding, args.simplify_conditions)
    func_display = decompile_ai.get_enemy_function_formater(abst, scr_names.names, scr_skill_names.names)
    output = abst.display_decompilation(func_display)
    
    if args.show_output:
        print output

    # Write decompilation to a file
    with open(args.output_file, "w") as f:
        f.write( output )

