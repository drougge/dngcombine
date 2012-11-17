#!/usr/bin/env python
# -*- coding: iso-8859-1 -*-

from sys import argv
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

raws = [DNG(open(fn, "rb")) for fn in argv[1:]]

t = raws[0]
big = (1 << t.bitspersample) - 1
warned = False
c = Collector(t.bitspersample)
miny, minx, maxy, maxx = t.activearea

for y in range(t.height):
	for x in range(t.width):
		val = sum(r.get_pixel() for r in raws)
		if not (miny <= y < maxy and minx <= x < maxx):
			val /= len(raws)
		if val > big:
			if not warned:
				print "Warning: Clipped values"
				warned = True
			val = big
		c.put(val)

ofh = open("out.dng", "wb")
fh = t.fh
fh.seek(0)
ofh.write(fh.read(t.offset))
ofh.write(str(c))
fh.seek(t.raw_size, 1)
ofh.write(fh.read())
