#!/usr/bin/python
# coding: utf-8

# Contains functionality for unpacking EO skill data tables
# if run from the command line, will take a skill data table file and a skill name table
# and output all of the available information for each skill
#
# when calling this from outside, make sure to call set_game_specific_values()
# with the appropriate game code first
#
# written by TheOnlyOne (@modest_ralts)

import argparse
from sys import stderr
from struct import Struct
import convert_EOstring
import unpack_EO_name_table
from shared_helpers import *

import eo_value_lookup
from eo_value_lookup import game_codes

def parseArguments():
    # Create argument parser
    parser = argparse.ArgumentParser(description="Parses an Etrian Odyssey skill data table and places the result in an output file.")

    # Positional mandatory arguments
    parser.add_argument("game", choices=game_codes, help="which game the data is from")
    parser.add_argument("input_name_file", help="name of the file containing the raw name table")
    parser.add_argument("input_skill_file", help="name of the file containing the skill data table")
    parser.add_argument("output_file", help="name of the file in which to place the output") 

    # Optional arguments
    parser.add_argument("--name_index_width", type=int, choices=[2,4], default=2, help="width, in bytes, of the indexes at the start of the name table")
    parser.add_argument("--hide_raw_name", action="store_true", help="raw skill names will not be displayed")
    parser.add_argument("--show_output", action="store_true", help="output will be printed to console in addition to being saved to the output_file")
    parser.add_argument("--hide_unknowns", action="store_true", help="messages will not be printed to stderr if unknown characters or unkown parts of skill data are encountered")
    parser.add_argument("--hide_raw_data", action="store_true", help="skill data will not have the raw hex values displayed alongside the readable data")

    # Print version
    parser.add_argument("--version", action="version", version='%(prog)s - Version 1.0')

    # Parse arguments
    args = parser.parse_args()

    return args


num_level_tables = 0
level_table_size = 0
skill_types = {}
requirements_flags = {}
target_types = {}
target_teams = {}
stat_modifier_stacks = {}
stat_modifier_types = {}
damage_type_flags = {}
ailment_kinds = {}
ailment_flags = {}
level_data_types = {}

# Create an unpacker based on the game
def get_game_unpacker(game):
    if game == "EOU":
        return Struct("<BBHH4B5HI160I")
    if game == "EO3":
        return Struct("<BBHH4B5HI88i")


# Modifies values and maps that are game specific
def set_game_specific_values(game):
    global num_level_tables
    global level_table_size

    global skill_types
    global requirements_flags
    global target_types
    global target_teams
    global stat_modifier_stacks
    global stat_modifier_types
    global damage_type_flags
    global ailment_kinds
    global ailment_flags
    global level_data_types

    if game == "EO3":
        num_level_tables = 8
        level_table_size = 10
    elif game == "EOU":
        num_level_tables = 10
        level_table_size = 15

    skill_types = eo_value_lookup.skill_types[game]
    requirements_flags = eo_value_lookup.requirements_flags[game]
    target_types = eo_value_lookup.target_types[game]
    target_teams = eo_value_lookup.target_teams[game]
    stat_modifier_stacks = eo_value_lookup.stat_modifier_stacks[game]
    stat_modifier_types = eo_value_lookup.stat_modifier_types[game]
    damage_type_flags = eo_value_lookup.damage_type_flags[game]
    ailment_kinds = eo_value_lookup.ailment_kinds[game]
    ailment_flags = eo_value_lookup.ailment_flags[game]
    level_data_types = eo_value_lookup.level_data_types[game]


# Data structure that stores the data for a single skill
class EO_skill_data_entry:

    # Parse a skill entry given the raw data and the game's unpacker
    # Suppress stderr by giving hide_unknowns = True
    # name is used to locate the unknowns
    def build_skill_entry(self, data, unpacker, name="", hide_unknowns=False):

        # prints to stderr if hide_unknowns is False
        def eprint(s):
            if not hide_unknowns:
                stderr.write(name + ": " + s + "\n")

        # check if there are True flags that don't have named indexes in the given map
        def check_unnamed_flags(flags, index_map, name):
            true_idx = []
            for idx, val in enumerate(flags):
                if val:
                    true_idx.append(idx)
            for idx in true_idx:
                if not (idx in index_map):
                     eprint( "There are unknown True flags in " + name + ": " + str(idx) )

        # unpack the full data into int-like values
        unpacked_data = list( unpacker.unpack(data) )

        # unpack a named value
        # returns the tuple (value, name)
        # index is the piece of the unpacked data that is relevant
        # table is the table in which to look for the name
        # width is the size in bytes, used for unknown printing
        # desc is a string saying what kind of data is being unpacked, used for unknown printing
        def unpack_named_value(index, table, width, desc):
            value = unpacked_data[index]
            name = ""
            if value in table:
                name = table[value]
            else:
                fmat = "{:#0" + str( 2 * (width + 1) ) + "x}"
                eprint("Unknown " + desc + ": " + fmat.format(value) )
                name = "<" + fmat.format(value) + ">"
            return value, name

        # unpack a bit flag list
        # returns the tuple (value, list of bools)
        # index is the piece of the unpacked data that is relevant
        # table is the table in which the names for flags are
        # num_bits is the size in bits
        # desc is a string saying what kind of data is being unpacked, used for unknown printing
        def unpack_flag_list(index, table, num_bits, desc):
            value = unpacked_data[index]
            flags = int_like_to_flag_list( value, num_bits )
            check_unnamed_flags(flags, table, desc)
            return value, flags
        
        # unk1 seems to always be 0x0A. Check if there are exceptions
        self.unk1 = unpacked_data[0]
        if self.unk1 != 0x0A:
            eprint("unk1 is not 0x0A! It is " + "{:#04x}".format(self.unk1) )

        # get the skill type
        self.skill_type, self.skill_type_name = unpack_named_value(1, skill_types, 1, "skill type")

        # get the usage requirements for this skill
        self.requirements, self.requirements_flags = unpack_flag_list(2, requirements_flags, 16, "Requirements")

        # get unk2
        self.unk2 = unpacked_data[3]
        self.unk2_flags = int_like_to_flag_list( self.unk2, 16 )

        # get the targeting type
        self.target_type, self.target_type_name = unpack_named_value(4, target_types, 1, "target type")
 
        # get the targeted team
        self.target_team, self.target_team_name = unpack_named_value(5, target_teams, 1, "target team")

        # unk3 seems to always be 0x04. Check if there are exceptions
        self.unk3 = unpacked_data[6]
        if self.unk3 != 0x04:
            eprint("unk3 is not 0x04! It is " + "{:#04x}".format(self.unk3) )

        # get the stat modifier stack
        self.stat_modifier_stack, self.stat_modifier_stack_name = unpack_named_value(7, stat_modifier_stacks, 1, "buff kind")

        # get the stat modifier type
        self.stat_modifier_type, self.stat_modifier_type_name = unpack_named_value(8, stat_modifier_types, 2, "buff type")

        # get the stat modifier damage types
        self.stat_modifier_damage_type, self.stat_modifier_damage_type_flags = unpack_flag_list(9, damage_type_flags, 16, "buff damage types")

        # get the damage types
        self.damage_type, self.damage_type_flags = unpack_flag_list(10, damage_type_flags, 16, "damage types")

        # get the ailment kind
        self.ailment_kind, self.ailment_kind_name = unpack_named_value(11, ailment_kinds, 2, "ailment kind")

        # get the ailment flags
        self.possible_ailments, self.possible_ailments_flags = unpack_flag_list(12, ailment_flags, 16, "ailment flags")

        # unk4 seems to always be 0x00. Check if there are exceptions
        self.unk4 = unpacked_data[13]
        if self.unk4 != 0x00:
            eprint("unk4 is not 0x00! It is " + "{:#04x}".format(self.unk4) )

        # parse the level tables
        # a level table will be stored as triple containing 
        # 1) the value for the data type,
        # 2) the name associated with this value, and
        # 3) the list of values for each level
        level_tables_base = 14
        for tbl in range(0, num_level_tables):
            our_base = level_tables_base + tbl * (level_table_size + 1)
            data_value = unpacked_data[ our_base ]
            data_value_name = ""
            if data_value in level_data_types:
                data_value_name = level_data_types[data_value]
            else:
                eprint("Unknown level data value: " + "{:#010x}".format(data_value) )
                data_value_name = "<" + "{:#010x}".format(data_value) + ">"
            level_values = []
            for level in range(0, level_table_size):
                level_values.append( unpacked_data[our_base + level + 1] )
            self.level_data.append( (data_value, data_value_name, level_values) )

    # Print a "nicely formatted" version of the skill data
    def display_skill(self, index, raw_name, name, args):

        # Creates output for a flag list, given its name table
        def display_flag_list(flags, name_table):
            names = []
            for idx, val in enumerate(flags):
                if val:
                    if idx in name_table:
                        name = name_table[idx]
                        if not args.hide_raw_data:
                            name += " (" + str(idx) + ")"
                        names.append( name )
                    else:
                        names.append( "<Flag #" + str(idx) + ">" )
            if not names:
                return "None"
            return ", ".join(names)

        # Creates output for normal values, given its name table
        def display_skill_data_value(value, name, width):
            if not args.hide_raw_data:
                fstring = "{:#0" + str( 2 * (width + 1) ) + "x}"
                name += " (" + fstring.format(value) + ")"
            return name

        output = ""

        # header
        line = ["Index: " + str(index), "Name: " + name]
        if not args.hide_raw_name:
            line.append( "(" + convert_EOstring.display_eostring(raw_name) + ")" )
        output += "\t".join(line) + "\n"

        # unk1
        output += "Unknown1:\t" + "{:#04x}".format(self.unk1) + "\n"

        # skill type
        output += "Skill Type:\t" + display_skill_data_value(self.skill_type, self.skill_type_name, 1) + "\n"

        # requirements
        output += "Requirements:\t" + display_flag_list(self.requirements_flags, requirements_flags) + "\n"

        # unk2
        output += "Unknown2:\t" + "{:#06x}".format(self.unk2) + "\n"

        # target type
        output += "Target Type:\t" + display_skill_data_value(self.target_type, self.target_type_name, 1) + "\n"

        # target team
        output += "Target Team:\t" + display_skill_data_value(self.target_team, self.target_team_name, 1) + "\n"

        # unk3
        output += "Unknown3:\t" + "{:#04x}".format(self.unk3) + "\n"

        # stat modifier stack
        output += "Buff Kind:\t" + display_skill_data_value(self.stat_modifier_stack, self.stat_modifier_stack_name, 1) + "\n"

        # stat modifier type
        output += "Buff Type:\t" + display_skill_data_value(self.stat_modifier_type, self.stat_modifier_type_name, 2) + "\n"

        # stat modifier flags
        output += "Buff Flags:\t" + display_flag_list(self.stat_modifier_damage_type_flags, damage_type_flags) + "\n"

        # damage types
        output += "Damage Types:\t" + display_flag_list(self.damage_type_flags, damage_type_flags) + "\n"

        # ailment kind
        output += "Ailment effect:\t" + display_skill_data_value(self.ailment_kind, self.ailment_kind_name, 2) + "\n"
 
        # ailment flages
        output += "Ailments:\t" + display_flag_list(self.possible_ailments_flags, ailment_flags) + "\n"

        # unk4
        output += "Unknown4:\t" + "{:#010x}".format(self.unk4) + "\n"

        # level data
        just_size = 28
        def pad6(i):
            return str(i).ljust(6)
        output += "Level Table:\n"
        output += "param \\ level".rjust(just_size) + "  " + "".join( map(pad6, range(1, level_table_size + 1)) ) + "\n"
        for tbl in range(0, num_level_tables):
            tag, tag_name, vals = self.level_data[tbl]
            row = tag_name.rjust(just_size) + "  " + "".join( map(pad6, vals) ) + "\n"
            output += row
        output += "\n"

        return output

    # Create an empty skill entry
    def __init__(self):
        self.unk1 = 0
        self.skill_type = 0
        self.skill_type_name = ""
        self.requirements = 0
        self.requirements_flags = 16 * [False]
        self.unk2 = 0
        self.unk2_flags = 16 * [False]
        self.target_type = 0
        self.target_type_name = ""
        self.target_team = 0
        self.target_team_name = ""
        self.unk3 = 0
        self.stat_modifier_stack = 0
        self.stat_modifier_stack_name = ""
        self.stat_modifier_type = 0
        self.stat_modifier_type_name = ""
        self.stat_modifier_damage_type = 0
        self.stat_modifier_damage_type_flags = 16 * [False]
        self.damage_type = 0
        self.damage_type_flags = 16 * [False]
        self.ailment_kind = 0
        self.ailment_kind_name = ""
        self.possible_ailments = 0
        self.possible_ailments_flags = 16 * [False]
        self.unk4 = 0
        self.level_data = []

# unpack all skills into a list of skills
# data is the raw file data containing all of the skill entries
# unpacker is the game's unpacker, obtained from get_game_unpacker()
# names is a EO_name_table with a matching number of indices
# hide_unknowns gets passed on to the entry parser
def unpack_skills(data, unpacker, names, hide_unknowns=False):

    struct_size = unpacker.size
    skills = []

    for index in range(0, names.size):
        skill = EO_skill_data_entry()
        data_slice = data[index*struct_size : (1+index)*struct_size]
        if len(data_slice) < struct_size:
            print "End of file reached before finding data for every skill name."
        else:
            skill.build_skill_entry(data_slice, unpacker, names.names[index], args.hide_unknowns)
            skills.append(skill)

    return skills

# takes a converted name table and skill table filename,
# the game, and the hide_unknowns flag, and passes these
# on to unpack_skills after reading and using the,
def unpack_skills_from_file(name_table, skill_file, game, hide_unknowns=False):

    # Get this game's unpacker, and set it's specific values
    unpacker = get_game_unpacker(game)
    set_game_specific_values(game)

    data = ""
    with open(skill_file) as f:
        data = f.read()

    # parse all skills and add their display to the output
    return unpack_skills(data, unpacker, names, hide_unknowns)


if __name__ == '__main__':
    # Parse the arguments
    args = parseArguments()

    # Build the name table from the given file
    names = unpack_EO_name_table.EO_name_table()
    names.build_from_file(args.input_name_file, args.name_index_width, not args.hide_unknowns)

    # Build the skill table from the given file
    skills = unpack_skills_from_file(names, args.input_skill_file, args.game, args.hide_unknowns)

    output = ""
    for index, skill in enumerate(skills):
        output += skill.display_skill(index, names.raw_names[index], names.names[index], args)

    if args.show_output:
        print output

    # Write result to a file
    with open(args.output_file, "w") as f:
        f.write(output)
