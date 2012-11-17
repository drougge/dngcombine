#!/usr/bin/env python
# -*- coding: iso-8859-1 -*-

from sys import exit
from struct import pack
from optparse import OptionParser
from os.path import exists

from parse import DNG

class Collector:
	def __init__(self, bitspersample):
		self.bitspersample = bitspersample
		self.data = []
		self.have_bits = 0
		self.val = 0
	
	def _put_bits(self, val, bits):
		self.have_bits += bits
		self.val = (self.val << bits) | val
		diff = self.have_bits - 8
		if diff >= 0:
			self.data.append(chr(self.val >> diff))
			self.val &= (1 << diff) - 1
			self.have_bits = diff
	
	def put(self, val):
		bits = self.bitspersample
		while bits > 8:
			self._put_bits((val >> (bits - 8)) & 0xff, 8)
			val >>= 8
			bits -= 8
		if bits:
			self._put_bits(val & ((1 << bits) - 1), bits)
	
	def __str__(self):
		return "".join(self.data)

p = OptionParser("Usage: %prog [-a] input1.dng input2.dng [input3.dng [...]] output.dng")
p.add_option("-a", "--average", action="store_true", help="Average sample values (instead of summing)")
opts, args = p.parse_args()

if len(args) < 3:
	p.print_help()
	exit(1)

outfile = args[-1]
if exists(outfile):
	print "Cowardly refusing to overwrite", outfile
	exit(1)

raws = [DNG(open(fn, "rb")) for fn in args[:-1]]

t = raws[0]
big = (1 << t.bitspersample) - 1
warned = False
c = Collector(t.bitspersample)
miny, minx, maxy, maxx = t.activearea
average = opts.average

for y in range(t.height):
	for x in range(t.width):
		val = sum(r.get_pixel() for r in raws)
		if average or not (miny <= y < maxy and minx <= x < maxx):
			val /= len(raws)
		if val > big:
			if not warned:
				print "Warning: Clipped values"
				warned = True
			val = big
		c.put(val)

ofh = open(outfile, "wb")
fh = t.fh
fh.seek(0)
ofh.write(fh.read(t.offset))
ofh.write(str(c))
fh.seek(t.raw_size, 1)
ofh.write(fh.read())

if hasattr(t, "exposuretime_offset"):
	exposuretime = [0, 1]
	for r in raws:
		n = exposuretime[0] * r.exposuretime[1] + exposuretime[1] * r.exposuretime[0]
		d = exposuretime[1] * r.exposuretime[1]
		gcd, tmp = n, d
		while tmp:
			gcd, tmp = tmp, gcd % tmp
		exposuretime = [n // gcd, d // gcd]
	fh.seek(0)
	fmt = {"I": "<II", "M": ">II"}[fh.read(1)]
	ofh.seek(t.exposuretime_offset)
	ofh.write(pack(fmt, *exposuretime))
