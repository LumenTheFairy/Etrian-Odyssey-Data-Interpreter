#!/usr/bin/python

game_codes = ["EO3","EOU"]

# These maps give the base identities to much of the data in the skill table

# This is the broad type of the skill
skill_types = {
  "EO3" : { 
    0x00 : "STR-based",
    0x01 : "TEC-based",
    0x13 : "Stat Modification",
  },
  "EOU" : {
    0x00 : "STR-based",
    0x12 : "Ailment",
    0x13 : "Stat Modification",
  },
}

# Flags saying what is required to use the skill
# includes body parts that must be unbound and weapons that must be equiped
requirements_flags = {
  "EO3" : {
    0 : "Head",
    1 : "Arms",
    2 : "Legs",
  },
  "EOU" : {
    0 : "Head",
    1 : "Arms",
    2 : "Legs",
  }
}

# This is who or how many characters a skill targets
target_types = {
  "EO3" : {
    0x01 : "Single Target",
    0x02 : "Full Team Target",
    0x0A : "Self",
  },
  "EOU" : {
    0x01 : "Single Target",
    0x02 : "Full Team Target",
    0x0A : "Self",
    0x10 : "Full Line Target",
    0x1A : "Line Piercing",
  }
}

# This is the team that is targeted
target_teams = {
  "EO3" : {
    0x01 : "User's Team",
    0x02 : "User's Opponent",
  },
  "EOU" : {
    0x01 : "User's Team",
    0x02 : "User's Opponent",
    0x03 : "Both Teams",
  }
}

# This determines which stack the buff goes into (or leaves from)
stat_modifier_stacks = {
  "EO3" : {
    0x00 : "N/A",
    0x01 : "Buff",
    0x02 : "Debuff",
    0x03 : "Buff and Debuff Clearing",
  },
  "EOU" : {
    0x00 : "N/A",
    0x01 : "Buff",
    0x02 : "Debuff",
    0x03 : "Buff and Debuff Clearing",
  }
}

# This determines which stat is modified by a buff or debuff
stat_modifier_types = {
    0x00 : "N/A",
    0x01 : "Physical Attack",
    0x03 : "Physical and Elemental Attack",
    0x04 : "Physical Defense",
    0x0B : "Evasion",
  "EO3" : {
    0x00 : "N/A",
    0x01 : "Physical Attack",
    0x04 : "Physical Defense",
  },
  "EOU" : {
    0x00 : "N/A",
    0x01 : "Physical Attack",
    0x03 : "Physical and Elemental Attack",
    0x04 : "Physical Defense",
    0x0B : "Evasion",
  }
}

# Physical and Elemental damage types can be stacked together, so they are stored as flags
# this is used for an attack's damage type, as well as a buff's or debuff's damage increase/reduction
# this maps the index of the flag to the damage type
damage_type_flags = {
  "EO3" : {
    0 : "Cut",
    1 : "Bash",
    2 : "Stab",
    3 : "Fire",
    4 : "Ice",
    5 : "Volt",
    6 : "Almighty",
  },
  "EOU" : {
    0 : "Cut",
    1 : "Bash",
    2 : "Stab",
    3 : "Fire",
    4 : "Ice",
    5 : "Volt",
    6 : "Almighty",
  }
}

# Skills can affect ailments, by causing or healing them, this determines what happens
ailment_kinds = {
  "EO3" : {
    0x00 : "N/A",
    0x01 : "Cause",
    0x02 : "Heal",
  },
  "EOU" : {
    0x00 : "N/A",
    0x01 : "Cause",
    0x02 : "Heal",
  }
}

# Multiple ailments can potentially be caused by a single attack, so they are stored as flags
# this maps the index of the flag to the name of the ailment
ailment_flags = {
  "EO3" : {
    6 : "Blind",
  },
  "EOU" : {
    3 : "Sleep",
    6 : "Blind",
  }
}

# Each skill's parameters change as the skill levels (even for enemies)
# these parameters are listed in increasing level, prefixed by a value saying what that parameter affects
# this is a list of the parameter types
level_data_types = {
  "EO3" : {
    0x0000 : "_ne",
  },
  "EOU" : {
    0x0000 : "None",
    0x0001 : "TP Cost",
    0x0003 : "Speed Modifier",
    0x0004 : "Base Accuracy",
    0x0058 : "Base Ailment Infliction Rate",
    0x006A : "Base Damage",
    0x007B : "Base Poison Damage",
    0x0169 : "Buff Turn Duration",
    0x0177 : "Attack Buff Power",
    0x0178 : "Defense Buff Power",
    0x0185 : "Evasion Buff Power",
  }
}


# this stores the information associated with a native function in the AI scripts
class Native_Function():
    
    # create a native function from given data
    def __init__(self, func_index, num_params, has_retval, return_type, name, desc):
        self.func_index = func_index
        self.num_params = num_params
        self.has_retval = has_retval
        self.type = return_type
        self.name = name
        self.desc = desc

# list of known native functions
# arguments are passed in this order:
# top of the stack is the first argument, second to top is the second argument, etc.
native_functions = {
  "EO3" : {
    # The following have been fairly thouroughly tested, but I've not looked at the actual functions, so they could of course be wrong
    0x0080 : Native_Function(0x80, 1, True, "int", "rand", "rand(x) returns a random value in the range [0, x] (inclusive)"),
    0x0085 : Native_Function(0x85, 1, True, "int", "retrieve", "retrieve(id) returns the value stored for this entity at index id"),
    0x0086 : Native_Function(0x86, 2, False, "void", "store", "store(x, id) stores x to the storage for this entity at index id"),
    0x0088 : Native_Function(0x88, 0, True, "int", "turn_count", "turn_count() returns the currently displayed turn count"),
    0x0090 : Native_Function(0x90, 0, False, "void", "set_action_attack", "set_action_attack() sets the action to Attack"),
    0x0091 : Native_Function(0x91, 1, False, "void", "set_action_skill", "set_action_skill(x) sets the action to skill x"),
    0x0092 : Native_Function(0x92, 0, False, "void", "set_action_flee", "set_action_flee() sets the action to run away"),
    0x0093 : Native_Function(0x93, 0, False, "void", "set_action_defend", "set_action_defend() sets the action to Defend"),
    0x0095 : Native_Function(0x95, 2, False, "void", "set_action_leveled_skill", "set_action_leveled_skill(x, y) sets the action to skill x, and the skill will use level y"),
    0x00C0 : Native_Function(0xC0, 1, True, "bool", "hp_check", "hp_check(x) returns true iff entity's current hp% is <= x%"),

    # The following have not been carefully tested, but I have a decent guess of what they're used for
    # the preceding _ is an indication that it falls in this category; it gets stripped out in display
    0x0000 : Native_Function(0x00, 1, True, "bool", "_get_global_flag", "get_global_flag(id) gets the global flag with index id"),
    0x0001 : Native_Function(0x01, 1, False, "void", "_set_global_flag", "set_global_flag(id) sets the global flag with index id to 1"),
    0x0002 : Native_Function(0x02, 1, False, "void", "_unset_global_flag", "unset_global_flag(id) sets the global flag with index id to 0"),
    0x0003 : Native_Function(0x03, 1, False, "void", "_display_message", "display_message(id) shows the message with the given id, from the current script's message table. Halts script until player advances through the text."),
    0x0004 : Native_Function(0x04, 1, True, "bool", "_prompt_yes_no", "prompt_yes_no(id) shows the message with the given id, from the current script's message table. Halts script until player selects yes or no, and returns their decision."),
    0x0005 : Native_Function(0x05, 1, True, "bool", "_prompt_three_choices", "prompt_three_choices(id) shows the message with the given id, from the current script's message table. Halts script until player selects one of three choices, and returns their decision."),
    0x0006 : Native_Function(0x06, 1, True, "bool", "_prompt_four_choices", "prompt_four_choices(id) shows the message with the given id, from the current script's message table. Halts script until player selects one of four choices, and returns their decision."),
    0x0007 : Native_Function(0x07, 1, False, "void", "_fade_out", "fade_out(c) causes the game to fade to black if c is 0 or white if c is 1."),
    0x0008 : Native_Function(0x08, 1, False, "void", "_fade_in", "fade_in(c) causes the game to fade in from black if c is 0 or white if c is 1. Has no effect if fade_out() has not been called."),
    0x000C : Native_Function(0x0C, 1, False, "void", "_wait", "wait(t) causes the game to idle for t frames"),
    0x0012 : Native_Function(0x12, 2, False, "void", "_set_message_party_member", "set_message_party_member(slot, member) tells the message string code 0x8043<slot> to display the name of the given member."),
    0x0013 : Native_Function(0x13, 2, True, "party member", "_get_party_member", "get_party_member(x, y) fetches something like a party member pointer. x seems to be 0: first member, 1: last member, 2: random member; I have no idea what y does."),
    0x0014 : Native_Function(0x14, 3, False, "void", "_play_music", "play_music(id, t, x) starts playing the music with the given id, taking t frames to fade out from the previous song. I don't know what x does."),
    0x0015 : Native_Function(0x15, 1, False, "void", "_stop_music", "stop_music(t) fades out the current music in t frames."),
    0x0016 : Native_Function(0x16, 0, True, "int", "_get_music", "get_music() fetches the id of the currently playing music. -1 if the music is stopped."),
    0x0020 : Native_Function(0x20, 1, True, "int", "_get_character_level", "get_character_level(member) gets the level of the given party member."),
    0x0021 : Native_Function(0x21, 1, True, "int", "_get_character_class", "get_character_class(member) gets the class id of the given party member."),
    0x002A : Native_Function(0x2A, 1, False, "bool", "_play_sfx_1", "play_sfx_1(id) plays the sound effect with the given id from sfx group 1."),
    0x002D : Native_Function(0x2D, 1, False, "bool", "_play_sfx_2", "play_sfx_2(id) plays the sound effect with the given id from sfx group 2."),
    0x001D : Native_Function(0x1D, 2, False, "void", "_set_message_number_display", "set_message_number_display(slot, x) tells the message string code 0x8010<slot> to display the number x."),
    0x001E : Native_Function(0x1E, 0, True, "int", "_party_size", "party_size() returns the number of characters curently in the party."),
    0x0030 : Native_Function(0x30, 1, False, "void", "_take_step", "take_step(d) causes the party to take a step in the given direction (relative to the current heading.) Allows you to walk through walls. Values for d are 0: Forward, 1: Backward, 2: Left, 3: Right."),
    0x0031 : Native_Function(0x31, 1, False, "void", "_set_direction", "set_direction(d) changes the direction the party is facing in the labyrinth. Values for d are 0: North, 1: South, 2: East, 3: West."),
    0x0032 : Native_Function(0x32, 3, False, "void", "_change_location", "change_location(x, y, d) changes the party's location to (x, y) on the currecnt floor, and changes their direction to d. Values for d are 0: North, 1: South, 2: East, 3: West."),
    0x0033 : Native_Function(0x33, 3, False, "void", "_show_bustup", "show_bustup(slot, char, effect) shows the given character in either slot 0 or 1. effect determines how they appear 0: fade in, 1: from right, 2: from left."),
    0x0034 : Native_Function(0x34, 2, False, "void", "_hide_bustup", "hide_bustup(slot, effect) removes the character from the given slot. effect determines how they leave 0: fade in, 1: to right, 2: to left."),
    0x0037 : Native_Function(0x37, 4, False, "void", "_start_battle", "start_battle(eg, f, bg, bgm) starts a battle with enemy group bg, with background bg, and music bgm. if f is 9, get blindsided, if f is >= 10, get pre-emptive attack, other values are neither (not sure on this one.)"),
    0x0039 : Native_Function(0x39, 1, False, "void", "_give_one_item", "give_one_item(id) gives the player one item of type id"),
    0x003A : Native_Function(0x3A, 2, False, "void", "_give_items", "give_items(id, x) gives the player x items of type id"),
    0x003B : Native_Function(0x3B, 1, False, "void", "_give_money", "give_money(x) gives the player x ental."),
    0x003C : Native_Function(0x3C, 1, True, "int", "_count_items", "count_items(id) returns the number of items of type id the player is holding."),
    0x003E : Native_Function(0x3E, 2, False, "void", "_remove_items", "remove_items(id, x) removes x items of type id from the player"),
    0x003F : Native_Function(0x3F, 4, True, "int", "_correct_map_percent", "correct_map_percent(x1, y1, x2, y2) returns the percentage of the floor the player has mapped correctly within the given rectangle."),
    0x0040 : Native_Function(0x40, 0, True, "int", "_floor_explored_percent", "floor_explored_percent() returns the percentage of the floor the player has 'explored'."),
    0x005E : Native_Function(0x5E, 0, True, "int", "_get_x_coord", "get_x_coord() returns the party's x coordinate on the map."),
    0x005F : Native_Function(0x5F, 0, True, "int", "_get_y_coord", "get_y_coord() returns the party's y coordinate on the map."),
    0x0065 : Native_Function(0x65, 8, False, "void", "_reward_screen", "reward_screen(exp, a, b, c, d, e, f, g) brings up the reward screen and gives the characters the given exp. The other parameters are ids for item drop rewards."),
    0x0071 : Native_Function(0x71, 1, False, "void", "_turn_party", "turn_party(d) changes the direction the party is facing in the labyrinth by turning them relative to their current heading. Values for d are 0: turn left, 1: turn right, 2: turn around."),
    0x0081 : Native_Function(0x81, 1, False, "void", "_set_flag", "set_flag(id) sets the flag with index id to 1"),
    0x0082 : Native_Function(0x82, 1, False, "void", "_unset_flag", "unset_flag(id) sets the flag with index id to 0"),
    0x0083 : Native_Function(0x83, 1, True, "bool", "_get_flag", "get_flag(id) retrieves the flag with index id"),
    0x0094 : Native_Function(0x94, 3, False, "void", "_set_action_call_allies", "set_action_call_allies(e, n, z) sets the action to call for n allies of type e. The purpose of z is unknown"),
    0x00A0 : Native_Function(0xA0, 0, False, "void", "_set_targeting_standard", "set_targeting_standard() sets the targeting scheme to standard targeting"),
    0x00A7 : Native_Function(0xA7, 0, False, "void", "_set_targeting_front", "set_targeting_front() sets the targeting scheme to front row"),
    0x00A8 : Native_Function(0xA8, 0, False, "void", "_set_targeting_back", "set_targeting_back() sets the targeting scheme to back row"),
    0x00A9 : Native_Function(0xA9, 0, False, "void", "_set_targeting_self", "set_target_self() sets the targeting scheme to target self"),
    0x00AE : Native_Function(0xAE, 1, False, "void", "_set_targeting_enemy_type", "set_targeting_enemy_type(id) sets the targeting scheme to enemies of type id"),
    0x00BE : Native_Function(0xBE, 1, False, "void", "_set_action_item", "set_action_item(x) set the action to use item x"),
    0x00C1 : Native_Function(0xC1, 1, True, "bool", "_tp_check", "tp_check(x) returns true iff entity's current tp% is <= x%"),
    0x00C2 : Native_Function(0xC2, 1, True, "bool", "_enemy_count_check", "enemy_count_check(x) returns true iff enemies remaining <= x"),
    0x00C7 : Native_Function(0xC7, 1, True, "bool", "_party_status_check", "party_status_check(b) checks if (any of?) the statuses given by the bits of b are 1, for (any of) the party? Or maybe for the player team?"),
    0x00C8 : Native_Function(0xC8, 1, True, "bool", "_status_check", "status_check(b) checks if (any of?) the statuses given by the bits of b are 1"),
    0x00D1 : Native_Function(0xD1, 1, True, "bool", "_enemy_exists", "enemy_exists(id) returns true iff an enemy of type id is in the battle"),
    0x00D2 : Native_Function(0xD2, 0, True, "int", "_floor_count", "floor_count() returns the current floor number"),
    0x00D5 : Native_Function(0xD5, 1, True, "int", "_count_enemies_of_type", "count_enemies_of_type(id) returns the number of enemies of type id in battle"),
    0x00F3 : Native_Function(0xF3, 2, False, "void", "_transform", "transform(x, y) tells set a transformation from enemy x to enemy y (I don't the the x is actually checked.)"),

    # The following have not been tested, and I don't know what they do, but I have a good guess of at least how they're used
    0x0096 : Native_Function(0x96, 3, False, "void", "_unk_96", "seems to be a team skill"),
    0x00AA : Native_Function(0xAA, 1, False, "void", "_set_targeting_10", "seems to set target to party member with given ailment"),
    0x00AD : Native_Function(0xAD, 1, False, "void", "_set_targeting_13", "seems to set target to opponent without given ailment"),
    0x00BA : Native_Function(0xBA, 0, False, "void", "_unk_ba", "maybe set target to party member with low hp"),
    0x00B6 : Native_Function(0xB6, 2, True, "int", "_unk_b6", "seems to check given line hp% and return number of chars below it?"),
    0x00B8 : Native_Function(0xB8, 1, True, "bool", "_unk_b8", "seems to check if player is using a given attack type"),
    0x00B9 : Native_Function(0xB9, 1, True, "bool", "_unk_b9", "seems to check if player is useing a given skill"),
    0x00C4 : Native_Function(0xC4, 1, True, "unknown", "_unk_c4", "seems to check full party hp"),
    0x00C6 : Native_Function(0xC6, 1, True, "unknown", "_unk_c6", "seems to check bit flags, maybe status"),
    0x00CA : Native_Function(0xCA, 1, True, "bool", "_unk_ca", "seems to check status flags for something"),
    0x00CB : Native_Function(0xCB, 0, True, "bool", "_unk_cb", "maybe checks if it's this enemy's first turn in battle"),
    0x00CD : Native_Function(0xCD, 2, True, "bool", "_unk_cd", "no idea, but it takes two arguments"),
    0x00D0 : Native_Function(0xD0, 2, True, "int", "_unk_d0", "maybe a buff counter of some kind"),
    0x00D3 : Native_Function(0xD3, 2, True, "unknown", "_unk_d3", "no idea"),
    0x00D4 : Native_Function(0xD4, 2, True, "unknown", "_unk_d4", "no idea"),
    0x00D8 : Native_Function(0xD8, 1, True, "bool", "_unk_d8", "seems to check a skill id for something"),
    0x00D9 : Native_Function(0xD9, 1, True, "unknown", "_unk_d9", "no idea"),
    0x00E1 : Native_Function(0xE1, 1, True, "unknown", "_unk_e1", "no idea"),
    0x00E4 : Native_Function(0xE4, 2, True, "unknown", "_unk_e4", "no idea"),
    0x00EA : Native_Function(0xEA, 1, True, "bool", "_unk_ea", "checking for existance of an enemy?"),
    0x00F5 : Native_Function(0xF5, 5, False, "void", "_unk_F5", "seems to be a crazy team skill"),

    # These are courtesy @violentlycar
    0x0089 : Native_Function(0x89, 0, True, "int", "_day_cycle", "Get time of day (Returns int; 0: dawn, 1: day, 2: dusk, 3: night)"),
    0x0096 : Native_Function(0x96, 3, False, "void", "_team_attack", "Perform team attack. Arguments are (int number_of_allies_needed, int id_of_monster_needed, int id_of_skill_to_cast). This function also handles setting the partner units to the \"ready\" state."),
    0x00A1 : Native_Function(0xA1, 0, False, "void", "_set_targeting_low_hp", "Target lowest HP (according to Dr. Fetus - not checked in code)"),
    0x00A2 : Native_Function(0xA2, 0, False, "void", "_set_targeting_high_hp", "Target highest HP (according to Dr. Fetus - not checked in code)"),
    0x00B4 : Native_Function(0xB4, 1, True, "bool", "_is_skill_castable", "Seems to check if the skill is castable. It calls the same function that causes skills to be greyed out on the menu due to lack of TP, bound body part, or other missing conditions."),
    0x00C3 : Native_Function(0xC3, 1, True, "bool", "_check_remaining_enemies", "Checks if the remaining enemy count is greater than the argument provided. Returns 0 if there are equal or more monsters than the provided argument, and returns 1 if there are fewer monsters. (It seems like every use of this in the base game has 1 for the argument, so I don't really understand this. I'm pretty sure my understanding of the code is correct, though.)"),
    0x00D6 : Native_Function(0xD6, 2, True, "bool", "_check_submerged", "Check if Narmer can submerge (Exclusive to the Narmer fight. Narmer may not submerge if he is already submerged, and he made not submerge if he emerged on the previous turn.)"),
    0x00D7 : Native_Function(0xD7, 2, False, "void", "_set_submerged", "Check if Narmer can submerge (Exclusive to the Narmer fight. Narmer may not submerge if he is already submerged, and he made not submerge if he emerged on the previous turn.)"),
    # Arguments for both the above are (int memory_offset, int bit_to_check). Specifically, what 0xD6 is doing is checking if bit 0x2 at character_data_struct+0x2EC is on. If so, it returns 1. If not, it returns 0. The "0" argument seems to be an offset to look at, but in EO3, this is always 0 because this function is used only on Narmer. 0xD7 is the same way, except instead of checking if the bit is set, it simply turns that bit off.
  },
  "EOU" : {
    # The following have been fairly thouroughly tested, but I've not looked at the actual functions, so they could of course be wrong
    0x0080 : Native_Function(0x80, 1, True, "int", "rand", "rand(x) returns a random value in the range [0, x] (inclusive)"),
    0x0085 : Native_Function(0x85, 1, True, "int", "retrieve", "retrieve(id) returns the value stored for this entity at index id"),
    0x0086 : Native_Function(0x86, 2, False, "void", "store", "store(x, id) stores x to the storage for this entity at index id"),
    0x0088 : Native_Function(0x88, 0, True, "int", "turn_count", "turn_count() returns the currently displayed turn count"),
    0x0090 : Native_Function(0x90, 0, False, "void", "set_action_attack", "set_action_attack() sets the action to Attack"),
    0x0091 : Native_Function(0x91, 1, False, "void", "set_action_skill", "set_action_skill(x) sets the action to skill x"),
    0x0092 : Native_Function(0x92, 0, False, "void", "set_action_flee", "set_action_flee() sets the action to run away"),
    0x0093 : Native_Function(0x93, 0, False, "void", "set_action_defend", "set_action_defend() sets the action to Defend"),
    0x0095 : Native_Function(0x95, 2, False, "void", "set_action_leveled_skill", "set_action_leveled_skill(x, y) sets the action to skill x, and the skill will use level y"),
    0x00C0 : Native_Function(0xC0, 1, True, "bool", "hp_check", "hp_check(x) returns true iff entity's current hp% is <= x%"),

    # The following have not been carefully tested, but I have a decent guess of what they're used for
    # the preceding _ is an indication that it falls in this category; it gets stripped out in display
    0x0000 : Native_Function(0x00, 1, True, "bool", "_get_global_flag", "get_global_flag(id) gets the global flag with index id"),
    0x0001 : Native_Function(0x01, 1, False, "void", "_set_global_flag", "set_global_flag(id) sets the global flag with index id to 1"),
    0x0002 : Native_Function(0x02, 1, False, "void", "_unset_global_flag", "unset_global_flag(id) sets the global flag with index id to 0"),
    0x0003 : Native_Function(0x03, 1, False, "void", "_display_message", "display_message(id) shows the message with the given id, from the current script's message table. Halts script until player advances through the text."),
    0x0004 : Native_Function(0x04, 1, True, "bool", "_prompt_yes_no", "prompt_yes_no(id) shows the message with the given id, from the current script's message table. Halts script until player selects yes or no, and returns their decision."),
    0x0005 : Native_Function(0x05, 1, True, "bool", "_prompt_three_choices", "prompt_three_choices(id) shows the message with the given id, from the current script's message table. Halts script until player selects one of three choices, and returns their decision."),
    0x0006 : Native_Function(0x06, 1, True, "bool", "_prompt_four_choices", "prompt_four_choices(id) shows the message with the given id, from the current script's message table. Halts script until player selects one of four choices, and returns their decision."),
    0x0007 : Native_Function(0x07, 1, False, "void", "_fade_out", "fade_out(c) causes the game to fade to black if c is 0 or white if c is 1."),
    0x0008 : Native_Function(0x08, 1, False, "void", "_fade_in", "fade_in(c) causes the game to fade in from black if c is 0 or white if c is 1. Has no effect if fade_out() has not been called."),
    0x000C : Native_Function(0x0C, 1, False, "void", "_wait", "wait(t) causes the game to idle for t frames"),
    0x0012 : Native_Function(0x12, 2, False, "void", "_set_message_party_member", "set_message_party_member(slot, member) tells the message string code 0x8043<slot> to display the name of the given member."),
    0x0013 : Native_Function(0x13, 2, True, "party member", "_get_party_member", "get_party_member(x, y) fetches something like a party member pointer. x seems to be 0: first member, 1: last member, 2: random member; I have no idea what y does."),
    0x0014 : Native_Function(0x14, 3, False, "void", "_play_music", "play_music(id, t, x) starts playing the music with the given id, taking t frames to fade out from the previous song. I don't know what x does."),
    0x0015 : Native_Function(0x15, 1, False, "void", "_stop_music", "stop_music(t) fades out the current music in t frames."),
    0x0016 : Native_Function(0x16, 0, True, "int", "_get_music", "get_music() fetches the id of the currently playing music. -1 if the music is stopped."),
    0x0020 : Native_Function(0x20, 1, True, "int", "_get_character_level", "get_character_level(member) gets the level of the given party member."),
    0x0021 : Native_Function(0x21, 1, True, "int", "_get_character_class", "get_character_class(member) gets the class id of the given party member."),
    0x002A : Native_Function(0x2A, 1, False, "bool", "_play_sfx_1", "play_sfx_1(id) plays the sound effect with the given id from sfx group 1."),
    0x002D : Native_Function(0x2D, 1, False, "bool", "_play_sfx_2", "play_sfx_2(id) plays the sound effect with the given id from sfx group 2."),
    0x001D : Native_Function(0x1D, 2, False, "void", "_set_message_number_display", "set_message_number_display(slot, x) tells the message string code 0x8010<slot> to display the number x."),
    0x001E : Native_Function(0x1E, 0, True, "int", "_party_size", "party_size() returns the number of characters curently in the party."),
    0x0030 : Native_Function(0x30, 1, False, "void", "_take_step", "take_step(d) causes the party to take a step in the given direction (relative to the current heading.) Allows you to walk through walls. Values for d are 0: Forward, 1: Backward, 2: Left, 3: Right."),
    0x0031 : Native_Function(0x31, 1, False, "void", "_set_direction", "set_direction(d) changes the direction the party is facing in the labyrinth. Values for d are 0: North, 1: South, 2: East, 3: West."),
    0x0032 : Native_Function(0x32, 3, False, "void", "_change_location", "change_location(x, y, d) changes the party's location to (x, y) on the currecnt floor, and changes their direction to d. Values for d are 0: North, 1: South, 2: East, 3: West."),
    0x0033 : Native_Function(0x33, 3, False, "void", "_show_bustup", "show_bustup(slot, char, effect) shows the given character in either slot 0 or 1. effect determines how they appear 0: fade in, 1: from right, 2: from left."),
    0x0034 : Native_Function(0x34, 2, False, "void", "_hide_bustup", "hide_bustup(slot, effect) removes the character from the given slot. effect determines how they leave 0: fade in, 1: to right, 2: to left."),
    0x0037 : Native_Function(0x37, 4, False, "void", "_start_battle", "start_battle(eg, f, bg, bgm) starts a battle with enemy group bg, with background bg, and music bgm. if f is 9, get blindsided, if f is >= 10, get pre-emptive attack, other values are neither (not sure on this one.)"),
    0x0039 : Native_Function(0x39, 1, False, "void", "_give_one_item", "give_one_item(id) gives the player one item of type id"),
    0x003A : Native_Function(0x3A, 2, False, "void", "_give_items", "give_items(id, x) gives the player x items of type id"),
    0x003B : Native_Function(0x3B, 1, False, "void", "_give_money", "give_money(x) gives the player x ental."),
    0x003C : Native_Function(0x3C, 1, True, "int", "_count_items", "count_items(id) returns the number of items of type id the player is holding."),
    0x003E : Native_Function(0x3E, 2, False, "void", "_remove_items", "remove_items(id, x) removes x items of type id from the player"),
    0x003F : Native_Function(0x3F, 4, True, "int", "_correct_map_percent", "correct_map_percent(x1, y1, x2, y2) returns the percentage of the floor the player has mapped correctly within the given rectangle."),
    0x0040 : Native_Function(0x40, 0, True, "int", "_floor_explored_percent", "floor_explored_percent() returns the percentage of the floor the player has 'explored'."),
    0x005E : Native_Function(0x5E, 0, True, "int", "_get_x_coord", "get_x_coord() returns the party's x coordinate on the map."),
    0x005F : Native_Function(0x5F, 0, True, "int", "_get_y_coord", "get_y_coord() returns the party's y coordinate on the map."),
    0x0065 : Native_Function(0x65, 8, False, "void", "_reward_screen", "reward_screen(exp, a, b, c, d, e, f, g) brings up the reward screen and gives the characters the given exp. The other parameters are ids for item drop rewards."),
    0x0071 : Native_Function(0x71, 1, False, "void", "_turn_party", "turn_party(d) changes the direction the party is facing in the labyrinth by turning them relative to their current heading. Values for d are 0: turn left, 1: turn right, 2: turn around."),
    0x0081 : Native_Function(0x81, 1, False, "void", "_set_flag", "set_flag(id) sets the flag with index id to 1"),
    0x0082 : Native_Function(0x82, 1, False, "void", "_unset_flag", "unset_flag(id) sets the flag with index id to 0"),
    0x0083 : Native_Function(0x83, 1, True, "bool", "_get_flag", "get_flag(id) retrieves the flag with index id"),
    0x0094 : Native_Function(0x94, 3, False, "void", "_set_action_call_allies", "set_action_call_allies(e, n, z) sets the action to call for n allies of type e. The purpose of z is unknown"),
    0x00A0 : Native_Function(0xA0, 0, False, "void", "_set_targeting_standard", "set_targeting_standard() sets the targeting scheme to standard targeting"),
    0x00A7 : Native_Function(0xA7, 0, False, "void", "_set_targeting_front", "set_targeting_front() sets the targeting scheme to front row"),
    0x00A8 : Native_Function(0xA8, 0, False, "void", "_set_targeting_back", "set_targeting_back() sets the targeting scheme to back row"),
    0x00A9 : Native_Function(0xA9, 0, False, "void", "_set_targeting_self", "set_target_self() sets the targeting scheme to target self"),
    0x00AE : Native_Function(0xAE, 1, False, "void", "_set_targeting_enemy_type", "set_targeting_enemy_type(id) sets the targeting scheme to enemies of type id"),
    0x00BE : Native_Function(0xBE, 1, False, "void", "_set_action_item", "set_action_item(x) set the action to use item x"),
    0x00C1 : Native_Function(0xC1, 1, True, "bool", "_tp_check", "tp_check(x) returns true iff entity's current tp% is <= x%"),
    0x00C2 : Native_Function(0xC2, 1, True, "bool", "_enemy_count_check", "enemy_count_check(x) returns true iff enemies remaining <= x"),
    0x00C7 : Native_Function(0xC7, 1, True, "bool", "_party_status_check", "party_status_check(b) checks if (any of?) the statuses given by the bits of b are 1, for (any of) the party? Or maybe for the player team?"),
    0x00C8 : Native_Function(0xC8, 1, True, "bool", "_status_check", "status_check(b) checks if (any of?) the statuses given by the bits of b are 1"),
    0x00D1 : Native_Function(0xD1, 1, True, "bool", "_enemy_exists", "enemy_exists(id) returns true iff an enemy of type id is in the battle"),
    0x00D2 : Native_Function(0xD2, 0, True, "int", "_floor_count", "floor_count() returns the current floor number"),
    0x00D5 : Native_Function(0xD5, 1, True, "int", "_count_enemies_of_type", "count_enemies_of_type(id) returns the number of enemies of type id in battle"),
    0x00F3 : Native_Function(0xF3, 2, False, "void", "_transform", "transform(x, y) tells set a transformation from enemy x to enemy y (I don't the the x is actually checked.)"),

    # The following have not been tested, and I don't know what they do, but I have a good guess of at least how they're used
    0x0096 : Native_Function(0x96, 3, False, "void", "_unk_96", "seems to be a team skill"),
    0x00AA : Native_Function(0xAA, 1, False, "void", "_set_targeting_10", "seems to set target to party member with given ailment"),
    0x00AD : Native_Function(0xAD, 1, False, "void", "_set_targeting_13", "seems to set target to opponent without given ailment"),
    0x00BA : Native_Function(0xBA, 0, False, "void", "_unk_ba", "maybe set target to party member with low hp"),
    0x00B6 : Native_Function(0xB6, 2, True, "int", "_unk_b6", "seems to check given line hp% and return number of chars below it?"),
    0x00B8 : Native_Function(0xB8, 1, True, "bool", "_unk_b8", "seems to check if player is using a given attack type"),
    0x00B9 : Native_Function(0xB9, 1, True, "bool", "_unk_b9", "seems to check if player is useing a given skill"),
    0x00C4 : Native_Function(0xC4, 1, True, "unknown", "_unk_c4", "seems to check full party hp"),
    0x00C6 : Native_Function(0xC6, 1, True, "unknown", "_unk_c6", "seems to check bit flags, maybe status"),
    0x00CA : Native_Function(0xCA, 1, True, "bool", "_unk_ca", "seems to check status flags for something"),
    0x00CB : Native_Function(0xCB, 0, True, "bool", "_unk_cb", "maybe checks if it's this enemy's first turn in battle"),
    0x00CD : Native_Function(0xCD, 2, True, "bool", "_unk_cd", "no idea, but it takes two arguments"),
    0x00D0 : Native_Function(0xD0, 2, True, "int", "_unk_d0", "maybe a buff counter of some kind"),
    0x00D3 : Native_Function(0xD3, 2, True, "unknown", "_unk_d3", "no idea"),
    0x00D4 : Native_Function(0xD4, 2, True, "unknown", "_unk_d4", "no idea"),
    0x00D8 : Native_Function(0xD8, 1, True, "bool", "_unk_d8", "seems to check a skill id for something"),
    0x00D9 : Native_Function(0xD9, 1, True, "unknown", "_unk_d9", "no idea"),
    0x00E1 : Native_Function(0xE1, 1, True, "unknown", "_unk_e1", "no idea"),
    0x00E4 : Native_Function(0xE4, 2, True, "unknown", "_unk_e4", "no idea"),
    0x00EA : Native_Function(0xEA, 1, True, "bool", "_unk_ea", "checking for existance of an enemy?"),
    0x00F5 : Native_Function(0xF5, 5, False, "void", "_unk_F5", "seems to be a crazy team skill"),

    # These are courtesy @violentlycar
    0x0089 : Native_Function(0x89, 0, True, "int", "_day_cycle", "Get time of day (Returns int; 0: dawn, 1: day, 2: dusk, 3: night)"),
    0x0096 : Native_Function(0x96, 3, False, "void", "_team_attack", "Perform team attack. Arguments are (int number_of_allies_needed, int id_of_monster_needed, int id_of_skill_to_cast). This function also handles setting the partner units to the \"ready\" state."),
    0x00A1 : Native_Function(0xA1, 0, False, "void", "_set_targeting_low_hp", "Target lowest HP (according to Dr. Fetus - not checked in code)"),
    0x00A2 : Native_Function(0xA2, 0, False, "void", "_set_targeting_high_hp", "Target highest HP (according to Dr. Fetus - not checked in code)"),
    0x00B4 : Native_Function(0xB4, 1, True, "bool", "_is_skill_castable", "Seems to check if the skill is castable. It calls the same function that causes skills to be greyed out on the menu due to lack of TP, bound body part, or other missing conditions."),
    0x00C3 : Native_Function(0xC3, 1, True, "bool", "_check_remaining_enemies", "Checks if the remaining enemy count is greater than the argument provided. Returns 0 if there are equal or more monsters than the provided argument, and returns 1 if there are fewer monsters. (It seems like every use of this in the base game has 1 for the argument, so I don't really understand this. I'm pretty sure my understanding of the code is correct, though.)"),
    # Note (by TheOnlyOne): I have no idea if these are used or are usable in EOU, but the rest of the functions seem to have carried over, so I'll leave them in
    0x00D6 : Native_Function(0xD6, 2, True, "bool", "_check_submerged", "Check if Narmer can submerge (Exclusive to the Narmer fight. Narmer may not submerge if he is already submerged, and he made not submerge if he emerged on the previous turn.)"),
    0x00D7 : Native_Function(0xD7, 2, False, "void", "_set_submerged", "Check if Narmer can submerge (Exclusive to the Narmer fight. Narmer may not submerge if he is already submerged, and he made not submerge if he emerged on the previous turn.)"),
    # Arguments for both the above are (int memory_offset, int bit_to_check). Specifically, what 0xD6 is doing is checking if bit 0x2 at character_data_struct+0x2EC is on. If so, it returns 1. If not, it returns 0. The "0" argument seems to be an offset to look at, but in EO3, this is always 0 because this function is used only on Narmer. 0xD7 is the same way, except instead of checking if the bit is set, it simply turns that bit off.

    # updated by Ragnar Homsar
    0x010A : Native_Function(0x10A, 2, False, "void", "rare_breed_func", "does something involving rare breed damage scaling"),
    0x00CC : Native_Function(0xCC, 1, True, "bool", "turn_is_multiple_of", "returns true if the turn is a multiple of the argument, false otherwise"), # technically not true - it's actually a multiple of how many actions the script owner has taken. this is a multiple of the turn in 99.9% of cases, but if it's on a FOE, it is possible for it to desync from the global turn counter
    0x00F6 : Native_Function(0xF6, 0, True, "bool", "rare_breed", "is the enemy a rare breed?"),
    0x00AB : Native_Function(0xAB, 1, False, "void", "set_targeting_status", "set targeting to party members that have the status bitflag passed as an argument"),
    0x010F : Native_Function(0x10F, 1, True, "bool", "self_in_state", "is the enemy currently in the state provided by the skill provided as an argument"),
    0x0110 : Native_Function(0x110, 3, False, "void", "queue_interruptable_action", "i have no clue what the final arg does"),
    0x00F9 : Native_Function(0x0F9, 0, True, "bool", "self_in_back_row", "is the user in the back row"),
    0x00EC : Native_Function(0xEC, 1, False, "void", "do_nothing", "do nothing and display a message passed as an argument"),
    0x00E3 : Native_Function(0xE3, 2, True, "bool", "self_possesses_skill_buff", "does the user have a buff originating from the skill in the second arg"),
    0x00F4 : Native_Function(0xF4, 1, True, "int", "check_other_enemy_hp", "returns the passed enemy's current HP percentage. i think this is only used for Ren checking Tlachtga's HP"),
    0x00B3 : Native_Function(0xB3, 0, True, "bool", "special_state", "is the enemy in a special state?")
  }
}