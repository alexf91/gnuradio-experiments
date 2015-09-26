#!/bin/sh

BASEDIR="$(pwd)"

# Install libosmocore-sq5bpf
git clone https://github.com/sq5bpf/libosmocore-sq5bpf || exit 1
cd libosmocore-sq5bpf
autoreconf -i || exit 1
./configure --prefix=$BASEDIR/install || exit 1
make -j || exit 1
mkdir $BASEDIR/install
make install || exit 1
#TODO set library path

# Install osmo-tetra-sq5bpf
cd $BASEDIR
git clone https://github.com/sq5bpf/osmo-tetra-sq5bpf || exit 2
cd osmo-tetra-sq5bpf/src || exit 2
git apply ../../osmo-python2.patch
make -j || exit 2

# Install telive
cd $BASEDIR
git clone https://github.com/sq5bpf/telive || exit 3
cd telive
INSTALLDIR=$BASEDIR/install/tetra
find ./ \( ! -regex '.*/\..*' \) -type f -exec sed -i "s@/tetra@$INSTALLDIR@" {} \; || exit 3
make || exit 3
mkdir $BASEDIR/install/tetra
sh install.sh || exit 3

# Install codecs
cd $BASEDIR/osmo-tetra-sq5bpf/etsi_codec-patches
wget http://www.etsi.org/deliver/etsi_en/300300_300399/30039502/01.03.01_60/en_30039502v010301p0.zip || exit 4
unzip -L en_30039502v010301p0.zip || exit 4
patch -p1 -N -E < codec.diff || exit 4
cd c-code
make || exit 4
cp cdecoder sdecoder $BASEDIR/install/tetra/bin || exit 4

