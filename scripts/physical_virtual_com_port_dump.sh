#!/bin/sh
# This links a physical COM port (e.g. /dev/ttyUSB0) to a virtual COM port
# at file: /tmp/ttyV0. The source COM port must be given as the first
# command line argument.
#
# This also creates an input and an output dump file
# stored at /tmp/in.txt and /tmp/out.txt
# 
echo "Linking $1 to /tmp/ttyV0, generating dump files /tmp/in.txt and /tmp/out.txt"
socat $1,raw,echo=0 \
SYSTEM:'tee /tmp/in.txt | socat - "PTY,link=/tmp/ttyV0,raw,echo=0,group-late=dialout,mode=660" | tee /tmp/out.txt'

# With added "waitslave" option
#socat $1,raw,echo=0 \
#SYSTEM:'tee /tmp/in.txt | socat - "PTY,link=/tmp/ttyV0,raw,echo=0,waitslave,group-late=dialout,mode=660" | tee /tmp/out.txt'
