#!/bin/bash

# run conversion on all of the EO3 data I know how to convert
# gives only the nice output and supresses unknowns
# assumes directory structure:
# ./EO3/
#     AI/
#     Enemy/*
#     Item/*
#     Skill/*
#   ...
# and ./out_EO3/ with the same folders but empty, except for the AI/ folder
# see decompile_all_EO3_ai.py for the correct output AI/ folder structure

# string tables
./unpack_EO_name_table.py  --hide_raw --hide_pos --hide_alerts EO3/Enemy/enemynametable.tbl out_EO3/Enemy/enemynametable.tsv

./unpack_EO_name_table.py  --hide_raw --hide_pos --hide_alerts EO3/Skill/enemyskillnametable.tbl out_EO3/Skill/enemyskillnametable.tsv
./unpack_EO_name_table.py  --hide_raw --hide_pos --hide_alerts EO3/Skill/playerskillnametable.tbl out_EO3/Skill/playerskillnametable.tsv
./unpack_EO_name_table.py  --hide_raw --hide_pos --hide_alerts EO3/Skill/limitskillstringstable.tbl out_EO3/Skill/limitskillstringstable.tsv
./unpack_EO_name_table.py  --hide_raw --hide_pos --hide_alerts --index_width 4 EO3/Skill/skillcustomtable.tbl out_EO3/Skill/skillcustomtable.tsv

./unpack_EO_name_table.py  --hide_raw --hide_pos --hide_alerts EO3/Item/equipitemnametable.tbl out_EO3/Item/equipitemnametable.tsv
./unpack_EO_name_table.py  --hide_raw --hide_pos --hide_alerts EO3/Item/limititemnametable.tbl out_EO3/Item/limititemnametable.tsv
./unpack_EO_name_table.py  --hide_raw --hide_pos --hide_alerts EO3/Item/seaitemequipeffect.tbl out_EO3/Item/seaitemequipeffect.tsv
./unpack_EO_name_table.py  --hide_raw --hide_pos --hide_alerts EO3/Item/seaitemname.tbl out_EO3/Item/seaitemname.tsv
./unpack_EO_name_table.py  --hide_raw --hide_pos --hide_alerts EO3/Item/useitemnametable.tbl out_EO3/Item/useitemnametable.tsv

# skill tables
./unpack_EO_skill_table.py --hide_raw_name --hide_raw_data --hide_unknowns EO3 EO3/Skill/enemyskillnametable.tbl EO3/Skill/enemyskilltable.tbl out_EO3/Skill/enemyskilltable.txt
./unpack_EO_skill_table.py --hide_raw_name --hide_raw_data --hide_unknowns EO3 EO3/Skill/playerskillnametable.tbl EO3/Skill/playerskilltable.tbl out_EO3/Skill/playerskilltable.txt

# disassembly
./disassemble_all_EO3_ai.sh

# decompilation
./decompile_all_EO3_ai.py --flatten_conditionals --constant_folding --simplify_conditions
