#!/usr/bin/python
# coding: utf-8

# Decompiles all AI files, naming, to the extent possible, skills
# and the entities that use each AI file (if any)
# assumes directory structure:
# ./EO3/
#     AI/
#       BtlBSTScrFileTable.tbl
#       BtlNPCScrFileTable.tbl
#       BtlScrFileTable.tbl
#       *.bf
#     Skills/
#       enemyskillnametable.tbl
#       playerskillnametable.tbl
#       ...
#     Enemy/
#       enemynametable.tbl
#       ...
#     ...
#   out_EO3/
#     AI/
#       decompiled/
#         enemy/
#         ally/
#         summon/
#       ...
#   ...
# written by TheOnlyOne (@modest_ralts)

import argparse
from sys import stderr
import os
import unpack_EO_name_table
import unpack_ai_proc_list
import unpack_ai
import decompile_ai

def parseArguments():
    # Create argument parser
    parser = argparse.ArgumentParser(description="Decompiles all Etrian Odyssey 3 AI files, naming skills and entities to the extent possible.")

    parser.add_argument("--fully_optimize", action="store_true", help="all optimization passes will be performed on the code; specific optimization flags will be ignored")
    parser.add_argument("--flatten_conditionals", action="store_true", help="(if . else if . else .) will be converted to (if . elif . else.) when permissable to reduce the nesting depth and resulting indentation of code")
    parser.add_argument("--flatten_elses", action="store_true", help="(if t return else f ) will be converted to (if t return f) when permissable to reduce the nesting depth and resulting indentation of code")
    parser.add_argument("--constant_folding", action="store_true", help="any arithmetic containing only constants will be replaced with the value of that expression")
    parser.add_argument("--simplify_conditions", action="store_true", help="boolean conditions will be simplified when it is permissable; see docs/ai_notes.txt for some warnings about this flag")

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
    scr_names.build_from_file("EO3/Enemy/enemynametable.tbl", 2, False)
    # Build the enemy skill name table
    scr_skill_names = unpack_EO_name_table.EO_name_table()
    scr_skill_names.build_from_file("EO3/Skill/enemyskillnametable.tbl", 2, False)
    # Build the player skill name table
    scrn_skill_names = unpack_EO_name_table.EO_name_table()
    scrn_skill_names.build_from_file("EO3/Skill/playerskillnametable.tbl", 2, False)
    # Build the procedure name list for enemies
    scr_proc_list = unpack_ai_proc_list.get_procedure_names("EO3/AI/BtlScrFileTable.tbl", scr_names.size)

    # holds all info in, and determined about a single AI file
    class AI_Info():

        # return a string with the full output destiation, including path and filename
        def get_full_output_name(self):
            # common directory
            output = "out_EO3/AI/decompiled/"
            
            # subdirectory based on type
            if self.type == "scr":
                output += "enemy/"
            elif self.type == "scrn":
                output += "ally/"
            elif self.type == "scrb":
                output += "summon/"

            # name used is just the first in the possible name list, or the original filename if there is none
            if self.possible_names:
                output += self.possible_names[0].replace(' ', '_')
            else:
                output += self.filename[:-3]
            
            # add a version number if necessary
            if self.version > 0:
                output += "_" + str(self.version)

            # extension
            output += ".txt"

            return output

        # computes everything about the ai from its file
        def __init__(self, subdir, filename):
            # name analysis
            self.filename = filename
            name_info = file[:-3].split('_', 2)  # 'AI_scr?_name.bf'
            self.type = name_info[1]
            listed_proc_name = '_'.join(name_info[1:])
            self.possible_names = []
            for idx, proc_name in enumerate(scr_proc_list):
                if proc_name == listed_proc_name:
                    self.possible_names.append( scr_names.names[idx] )

            #if self.type == "scr" and not self.possible_names:
            #    print "No possible name found: " + self.filename
            # TODO: this loop for sea allies and summons once a name list is found

            # when there are multiple enemies with the same name, use a non-zero version to distinguish them
            self.version = 0
            
            self.flow = unpack_ai.Flow_File(os.path.join(subdir, filename))
            self.basic_blocks, self.proc_info, self.special_labels = decompile_ai.abstract_flow(self.flow)
            self.abst = decompile_ai.ABST(self.basic_blocks, self.proc_info, self.special_labels)
            if args.fully_optimize:
              self.abst.optimize_abst()
            else:
              self.abst.optimize_abst(args.flatten_conditionals, args.flatten_elses, args.constant_folding, args.simplify_conditions)

    decompile_ai.set_game_specific_values("EO3")
    ai_info = []            

    for subdir, dirs, files in os.walk('EO3/AI/'):
        for file in files:
            if file.endswith('.bf'):
                # create the raw disassembly flow
                ai_info.append( AI_Info(subdir, file) )
    
    # adds versions to AIs with the same first possible name
    # note that this is not particularly efficient
    for out_idx, out_info in enumerate(ai_info):
        matches = [out_info]
        for in_idx, in_info in enumerate(ai_info):
            if out_idx != in_idx and out_info.possible_names and in_info.possible_names:
                if out_info.possible_names[0] == in_info.possible_names[0]:
                    matches.append(in_info)
        if len(matches) > 1:
            matches.sort(key=lambda i : i.filename)
            for in_idx, in_info in enumerate(matches):
                in_info.version = in_idx + 1

    for info in ai_info:
        
        # header info
        output = []
        if info.possible_names:
            output += ["Name: " + info.possible_names[0] ]
            if info.version > 0:
                output[0] += " (version " + str(info.version) + ")"
        output += ["Original filename: " + info.filename]
        output += [""]
        if info.type == "scr":
            func_display = decompile_ai.get_enemy_function_formater(info.abst, scr_names.names, scr_skill_names.names)
            output += [info.abst.display_decompilation(func_display)]
        else:
            output += [info.abst.display_decompilation()]

        # Write decompilation to a file
        with open(info.get_full_output_name(), "w") as f:
            f.write( "\n".join(output) )
