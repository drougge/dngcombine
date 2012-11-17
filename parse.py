#!/usr/bin/env python
# -*- coding: iso-8859-1 -*-

from wellpapp.util import TIFF
from sys import argv

fh = open(argv[1], "rb")
t = TIFF(fh)
ifd = t.subifd[0]
width, height = t.ifdget(ifd, 256)[0], t.ifdget(ifd, 257)[0]
bitspersample = t.ifdget(ifd, 258)[0]
assert t.ifdget(ifd, 277)[0] # SamplesPerPixel
z = t.ifdget(ifd, 279)[0]
off = t.ifdget(ifd, 273)[0]

data = """P5
4000 3000
255
"""
ofh = open("out.pgm", "wb")
ofh.write(data)

fh.seek(off)
data = fh.read(z)

have_bits = 0
val = 0
out = []
row = []
imax = 0
values = []

def put(v):
	global row, imax
	row.append(v)
	if len(row) == width:
		row = row[:4000]
		m = max(row)
		print len(out), m
		imax = max(imax, m)
		out.append("".join(chr(v >> 4) for v in row))
		values.extend(row)
		row = []

for byte in map(ord, data):
	if have_bits + 8 > bitspersample:
		want = bitspersample - have_bits
		mask = (1 << want) - 1
		have_bits = 8 - want
		put(val << want | (byte & ~mask) >> have_bits)
		val = byte & mask
	else:
		val = val << 8 | byte
		have_bits += 8
		if have_bits == bitspersample:
			put(val)
			have_bits = val = 0

print imax
ofh.write("".join(out))
