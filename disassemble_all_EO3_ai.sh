for f in EO3/AI/*.bf; do
    filename="${f##*/}"
    filename="${filename%.*}"
    ./unpack_ai.py EO3/AI/$filename.bf out_EO3/AI/disassembled/$filename.txt
done
