#!/bin/bash

# https://github.com/waydroid/waydroid/issues/788#issuecomment-2162386712
# author: qwerty12356-wart
function CheckHex {
    #file path, Ghidra offset, Hex to check
    commandoutput="$(od $1 --skip-bytes=$(($2-0x100000)) --read-bytes=$((${#3} / 2)) --endian=little -t x1 -An file | sed 's/ //g')"
    if [ "$commandoutput" = "$3" ]; then
        echo "1"
    else
        echo "0"
    fi
}

function PatchHex {
    #file path, ghidra offset, original hex, new hex
    file_offset=$(($2-0x100000))
    if [ $(CheckHex $1 $2 $3) = "1" ]; then
        hexinbin=$(printf $4 | xxd -r -p)
        echo -n $hexinbin | dd of=$1 seek=$file_offset bs=1 conv=notrunc;
        tmp="Patched $1 at $file_offset with new hex $4"
        echo $tmp
        elif [ $(CheckHex $1 $2 $4) = "1" ]; then
        echo "Already patched"
    else
        echo "Hex mismatch!"
    fi
}