#!/bin/sh
# This creates two virtual COM ports at files: /tmp/ttyV0 and /tmp/ttyV1.
#
# This also creates an input and an output dump file
# stored at /tmp/in.txt and /tmp/out.txt
# 
echo "Creating /tmp/ttyV0 and /tmp/ttyV1, generating dump files /tmp/in.txt and /tmp/out.txt"
socat "PTY,link=/tmp/ttyV0,raw,echo=0,group-late=dialout,mode=660,raw,echo=0" \
SYSTEM:'tee /tmp/in.txt | socat - "PTY,link=/tmp/ttyV1,raw,echo=0,group-late=dialout,mode=660" | tee /tmp/out.txt'

# With added "waitslave" option
#socat "PTY,link=/tmp/ttyV0,raw,echo=0,waitslave,group-late=dialout,mode=660,raw,echo=0" \
#SYSTEM:'tee /tmp/in.txt | socat - "PTY,link=/tmp/ttyV1,raw,echo=0,waitslave,group-late=dialout,mode=660" | tee /tmp/out.txt'
