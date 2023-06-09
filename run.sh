#!/usr/bin/env bash

current_directory=$(pwd)
dev_directory="$(dirname "$(readlink -f "$0")")"

# Store the first argument in a variable
operation_type="$1"

# Remove the first argument from the list
shift

if [ "$operation_type" == "generate" ]; then
    modal run ${dev_directory}/main.py --directory "${current_directory}" "$@"
elif [ "$operation_type" == "iterate" ]; then
    modal run ${dev_directory}/iterate.py --variation "iterate" --directory "${current_directory}" "$@"
elif [ "$operation_type" == "explain" ]; then
    modal run ${dev_directory}/iterate.py --variation "explain" --directory "${current_directory}" "$@"
else
    echo "Error: invalid operation type. Choose either 'generate' or 'iterate'."
    exit 1
fi
