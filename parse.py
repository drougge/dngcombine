#!/usr/bin/env python
# -*- coding: iso-8859-1 -*-

from wellpapp.util import TIFF

class DNG:
	def __init__(self, fh):
		self.fh = fh
		t = TIFF(fh)
		ifd = t.subifd[0]
		self.width, self.height = t.ifdget(ifd, 256)[0], t.ifdget(ifd, 257)[0]
		self.bitspersample = t.ifdget(ifd, 258)[0]
		assert t.ifdget(ifd, 277)[0] # SamplesPerPixel
		self.raw_size = t.ifdget(ifd, 279)[0]
		self.offset = t.ifdget(ifd, 273)[0]
		fh.seek(self.offset)
		self.data = fh.read(self.raw_size)
		assert len(self.data) == self.raw_size
		self._pos = 0
		self._have_bits = 0
		self._val = 0
	
	def get_pixel(self):
		byte = ord(self.data[self._pos])
		self._pos += 1
		if self._have_bits + 8 > self.bitspersample:
			want = self.bitspersample - self._have_bits
			mask = (1 << want) - 1
			self._have_bits = 8 - want
			res = self._val << want | (byte & ~mask) >> self._have_bits
			self._val = byte & mask
			return res
		else:
			self._val = self._val << 8 | byte
			self._have_bits += 8
			if self._have_bits == self.bitspersample:
				res = self._val
				self._have_bits = self._val = 0
				return res
			else:
				return self.get_pixel()

if __name__ == "__main__":
	from sys import argv
	raw = DNG(open(argv[1], "rb"))
	ofh = open("out.pgm", "wb")
	ofh.write("P5\n4000 3000\n255\n")
	for r in range(raw.height):
		ofh.write("".join(chr(raw.get_pixel() >> 4) for p in range(raw.width))[:4000])
