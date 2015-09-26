#!/bin/sh

BASEDIR="$(pwd)"
TERMINAL="xfce4-terminal --hide-menubar"

cd $BASEDIR/osmo-tetra-sq5bpf/src
$TERMINAL --command="./receiver1 1" &
RECEIVER_PID=$!
sleep 5

cd $BASEDIR/telive
$TERMINAL --geometry=203x60 --command="./rxx" &
RXX_PID=$!
sleep 5

cd $BASEDIR/install/tetra/bin
$TERMINAL --command="./tetrad" &
TETRAD_PID=$!
sleep 5

cd $BASEDIR//telive/gnuradio-companion
gnuradio-companion telive_1ch_gr37.grc

