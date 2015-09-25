#!/usr/bin/env python

import sys
import socket
import enum
import struct
import math
from datetime import datetime
import re
import setproctitle

class Source(object):
    def bitstream(self):
        raise NotImplementedError(self.__class__.__name__)

class TCPSource(Source):
    def __init__(self, ip='127.0.0.1', port=58000):
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.connect((ip, port))
        self.sock = sock

    def bitstream(self):
        while True:
            for bit in self.sock.recv(1024):
                yield bit

class FileSource(Source):
    def __init__(self, path):
        self._fd = open(path, 'rb')

    def bitstream(self):
        for bit in self._fd.read():
            yield bool(bit)

class SequenceCounter(object):
    def __init__(self):
        self.last = False
        self.count = 0

    def add_sample(self, sample):
        sample = bool(sample)
        ret = None
        if self.last == sample:
            self.count += 1
        else:
            ret = (self.last, self.count)
            self.count = 0

        self.last = sample
        return ret

class SymbolDecoder(object):
    class State(enum.Enum):
        Unlocked = 0 # Wait for preamble
        Locked   = 1 # Locked, record samples

    def __init__(self, symb_length, tolerance=0.1, locklength=100, inverted=False):
        self.symb_length = symb_length
        self.tolerance = tolerance
        self.locklength = locklength
        self.inverted = inverted

        self.state = self.State.Unlocked
        self.last = False
        self.samp_count = 0
        self.preamb_count = 0

        self.decoded = []

    def add_sample(self, sample):
        ret = None
        sample = sample ^ self.inverted

        if self.state == self.State.Unlocked:
            if self.last != sample:
                symbols = self.samp_count / self.symb_length
                if ((1-self.tolerance) <= self.samp_count / self.symb_length
                        <= (1+self.tolerance)):
                    self.preamb_count += 1
                    self.decoded.append(self.last)
                else:
                    self.preamb_count = 0
                    self.decoded = []

                self.samp_count = 0
            else:
                self.samp_count += 1

            if self.preamb_count == self.locklength:
                self.state = self.State.Locked
                self.preamb_count = 0
                self.samp_count = 0

        elif self.state == self.State.Locked:
            if self.samp_count % self.symb_length == self.symb_length // 2:
                self.decoded.append(sample)

            if self.last != sample:
                if self.samp_count < self.symb_length * (1-self.tolerance):
                    self.state = self.State.Unlocked
                    ret =  ''.join([str(int(x)) for x in self.decoded])

                self.samp_count = 0
            else:
                self.samp_count += 1

        self.last = sample
        return ret

class Codeword(object):
    @staticmethod
    def create(codeword):
        if codeword == '01111010100010011100000110010111':
            return Idle()

        if int(codeword[0]) == 0:
            return Address(codeword)
        elif int(codeword[0]) == 1:
            return Message(codeword)
        else:
            raise ValueError()

class Address(Codeword):
    address  = property(lambda self: self._address)
    function = property(lambda self: self._function)

    def __init__(self, codeword):
        assert int(codeword[0]) == 0 and len(codeword) == 32

        self._address  = int(codeword[1:19], 2)
        self._function = int(codeword[19:21], 2)
        self._bch      = int(codeword[21:31], 2)
        self._parity   = int(codeword[31], 2)

    def __str__(self):
        return '<Address {}-{}>'.format(hex(self._address), self._function)


class Message(Codeword):
    message = property(lambda self: self._message)

    def __init__(self, codeword):
        assert int(codeword[0]) == 1 and len(codeword) == 32

        self._message  = int(codeword[1:21], 2)
        self._bch      = int(codeword[21:31], 2)
        self._parity   = int(codeword[31], 2)

    def __str__(self):
        return '<Message {}>'.format(hex(self._message))


class Idle(Codeword):
    def __str__(self):
        return '<Idle>'


class PocsagDecoder(object):
    SYNC_WORD = '01111100110100100001010111011000'

    def decode(self, message):
        decoded = []
        # Split into batches
        for match in re.finditer(self.SYNC_WORD, message):
            start = match.end()
            batch = message[start:start+512]
            if len(batch) != 512:
                continue

            # Split into frames
            frames = [batch[i:i+64] for i in range(0, 512, 64)]
            for frame in frames:
                codeword1 = Codeword.create(frame[0:32])
                codeword2 = Codeword.create(frame[32:])
                decoded.append(codeword1)
                decoded.append(codeword2)

        return decoded

def codewords_to_string(codewords):
    address = None
    message = ''
    for codeword in codewords:
        if isinstance(codeword, Address):
            address = codeword.address
        elif isinstance(codeword, Message):
            message += bin(codeword.message)[2:].zfill(20)

    msg = ''
    if message:
        symbcount = len(message) // 7
        for i in range(symbcount):
            value = ''.join(reversed(message[i*7:(i+1)*7]))
            val = int(value, 2)
            msg += chr(val)

    if address:
        msg = '{} - {}'.format(hex(address)[2:], msg)

    return msg

def main():
    setproctitle.setproctitle('pocsag407')

    source = TCPSource()
    symb_decoder = SymbolDecoder(48, 0.2, inverted=True)
    decoder = PocsagDecoder()

    for bit in source.bitstream():
        symbols = symb_decoder.add_sample(bit)
        if symbols is not None:
            decoded = decoder.decode(symbols)
            msg = codewords_to_string(decoded)
            if msg != '':
                print(codewords_to_string(decoded))


if __name__ == '__main__':
    sys.exit(main() or 0)
