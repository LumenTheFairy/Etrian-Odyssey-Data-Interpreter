### Purpose and Usage

This repository contains a collection of scripts that I have written to convert raw files found in Etrian Odyssey 2, 3, 4, 5, U, and 2U into something more human readable:

-Name tables (`.tbl`): can be converted with `convert_EO_name_table.py`. Examples of files that use this format are enemy name tables and skill name tables.
-Skill tables (`.tbl`): can be converted with `convert_EO_skill_table.py`. For example, there are tables for enemy and player skills, giving the skills type and effects, and the power of the skills as it levels up.
-Message tables (`.mbm`): can be converted with `convert_msg.py`. For example, there are message tables for each facility's dialogues, and for each floor's events.
-Script files (`.bf`): can be simply disassembled with `unpack_ai.py` and they can be decompiled with `decompile_ai.py`. These script files are used for enemy AI, as well as for events/dialogue. Using `decompile_enemy_ai.py` on an enemy script can fill in some more information (such as replacing a skill id with its actual name.)

Command line parameters and options can be obtained for each of these by passing in `-h`. For an example of usage, `convert_all_EO3.sh` uses all of these scripts to convert a bunch of game files.

See the `docs/` folder for more detailed information about specific file formats.

### Limitations

Meaningful conversion is highly contingent on having names for various pieces of data. For example, if a value is being used as a damage type, the fact that the fourth least significant bit signifies "Fire" is something we just need to know. `eo_value_lookup.py` contains maps from raw data to names for things like this, so that the scripts can fill in this kind of information for us. These maps are highly incomplete, and likely vary quite a bit by game.
For decompilation in particular, having knowledge of the number of parameters a native function takes impacts the accuracy of the decompilation (they can be guessed, but if the guesses are incorect, the entire expression in which the function is used will be incorrect.) Having knowledge of the purpose of a native function is also required to actually understand the script's behavior.
Updating these maps with more information will greatly improve the readability of the outputs of the conversion scripts.

There are, of course, many file formats that are not handled here. AI Script decompilation was my main focus, so I only touched on a few other related file formats.
 
Aside from converting to and from eostrings, conversion back into raw files is not done by these scripts. The file format outlines in the `docs/` folder should give you a good start if you are interested in doing this.
