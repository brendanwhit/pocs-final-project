#!/bin/bash

echo $PWD

filename=$PWD"/test.txt"

echo $filename

while read -r line; do
    ./shockdetector.py $line
    echo $line
done < "$filename"
