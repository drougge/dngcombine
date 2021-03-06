#!/usr/bin/env python
# -*- coding: iso-8859-1 -*-

from sys import exit
from struct import pack
from optparse import OptionParser
from os.path import exists
from array import array

from parse import DNG

class Collector:
	def __init__(self, bitspersample):
		self.bitspersample = bitspersample
		self.data = array("B")
		self.write = self.data.write
		self.have_bits = 0
		self.val = 0
		if bitspersample == 16:
			self.put = self.put_16
		if bitspersample == 12:
			self.put = self.put_12
	
	def put_16(self, val):
		self.data.append(val >> 8)
		self.data.append(val & 0xff)
	
	def put_12(self, val):
		if self.have_bits:
			self.data.append((self.val << 4) | (val >> 8))
			self.data.append(val & 0xff)
			self.have_bits = 0
		else:
			self.data.append(val >> 4)
			self.val = val & 0xf
			self.have_bits = 4
	
	def _put_bits(self, val, bits):
		self.have_bits += bits
		self.val = (self.val << bits) | val
		diff = self.have_bits - 8
		if diff >= 0:
			self.data.append(self.val >> diff)
			self.val &= (1 << diff) - 1
			self.have_bits = diff
	
	def put(self, val):
		bits = self.bitspersample
		while bits > 8:
			self._put_bits((val >> (bits - 8)) & 0xff, 8)
			bits -= 8
		if bits:
			self._put_bits(val & ((1 << bits) - 1), bits)

p = OptionParser("Usage: %prog [options] input1.dng input2.dng [input3.dng [...]] output.dng")
p.add_option("-a", "--average", action="store_true", help="Average sample values (instead of summing)")
p.add_option("-b", "--blacklevel", type="int", help="Override black level")
p.add_option("-s", "--scale", type="float", help="Multiply samples by this")
opts, args = p.parse_args()

if len(args) < 3:
	p.print_help()
	exit(1)

outfile = args[-1]
if exists(outfile):
	print "Cowardly refusing to overwrite", outfile
	exit(1)

raws = [DNG(open(fn, "rb")) for fn in args[:-1]]
count = len(raws)

t = raws[0]
big = (1 << t.bitspersample) - 1
warned = False
c = Collector(t.bitspersample)
miny, minx, maxy, maxx = t.activearea
average = opts.average
if opts.blacklevel is not None:
	if average:
		print "Blacklevel is ignored for averaging"
		exit(1)
	blacklevel = opts.blacklevel
else:
	blacklevel = sum(r.blacklevel for r in raws[1:])
scale = opts.scale or 1

for y in range(t.height):
	for x in range(t.width):
		if average or not (miny <= y < maxy and minx <= x < maxx):
			val = sum(r.get_pixel() for r in raws) // count
		else:
			val = max(0, sum(r.get_pixel() for r in raws) - blacklevel)
		val = int(val * scale)
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
c.write(ofh)
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

if hasattr(t, "iso_offset"):
	from math import log10
	iso = 10 ** (sum(log10(r.iso[0]) for r in raws) / count)
	if average:
		iso /= count
	fh.seek(0)
	fmt = {"I": "<HII", "M": ">HII"}[fh.read(1)]
	ofh.seek(t.iso_offset + 2)
	ofh.write(pack(fmt, 4, 1, int(round(iso))))
