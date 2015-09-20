#!/bin/sh

if [ -z "$1" ]; then
    echo "Usage: %0 <animation> [ device ]"
    exit 1
fi

DEVICE="/dev/ttyACM0"
if [ -n "$2" ]; then
    DEVICE="$2"
fi

cat "$1" > /dev/ttyACM0

exit 0

