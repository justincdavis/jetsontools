#!/usr/bin/env bash

# Define a list of valid strings
submodules=()

# Iterate over the contents of the directory
for FILE in src/jetsontools/*;
do
    # Extract the filename from the full path
    filename=$(basename "$FILE")
    
    # Check if the filename is in the list of valid strings
    if [[ " ${submodules[*]} " =~ " $filename " ]]; then
        echo "Running $filename..."
        python3 -m mypy --follow-imports=silent $FILE
    else
        echo "Skipping $filename..."
    fi
done

# Define bool for checking entire src folder
check_all=false

# Check entire folder if bool is true
if [ "$check_all" = true ] ; then
    echo "Running mypy on entire src folder..."
    python3 -m mypy --follow-imports=silent src
fi
