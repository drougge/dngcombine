#!/usr/bin/env python
# -*- coding: iso-8859-1 -*-

class TIFF:
	"""Pretty minimal TIFF container parser"""
	
	types = {1: (1, "B"),  # BYTE
		 2: (1, None), # ASCII
		 3: (2, "H"),  # SHORT
		 4: (4, "I"),  # LONG
		 5: (8, "II"), # RATIONAL
		 # No TIFF6 fields, sorry
		}
	
	def __init__(self, fh, short_header=False):
		from struct import unpack
		self._fh = fh
		d = fh.read(4)
		if short_header:
			if d[:2] not in (b"II", b"MM"): raise Exception("Not TIFF")
		else:
			if d not in (b"II*\0", b"MM\0*"): raise Exception("Not TIFF")
		endian = {b"M": ">", b"I": "<"}[d[0]]
		self._up = lambda fmt, *a: unpack(endian + fmt, *a)
		self._up1 = lambda *a: self._up(*a)[0]
		if short_header:
			next_ifd = short_header
		else:
			next_ifd = self._up1("I", fh.read(4))
		self.reinit_from(next_ifd, short_header)
	
	def reinit_from(self, next_ifd, short_header=False):
		self.ifd = []
		self.subifd = []
		while next_ifd:
			self.ifd.append(self._ifdread(next_ifd))
			if short_header: return
			next_ifd = self._up1("I", self._fh.read(4))
		subifd = self.ifdget(self.ifd[0], 0x14a) or []
		for next_ifd in subifd:
			self.subifd.append(self._ifdread(next_ifd))
	
	def ifdget(self, ifd, tag):
		if tag in ifd:
			type, vc, off = ifd[tag]
			if type not in self.types: return None
			if isinstance(off, int): # offset
				self._fh.seek(off)
				tl, fmt = self.types[type]
				off = self._fh.read(tl * vc)
				if fmt: off = self._up(fmt * vc, off)
			if isinstance(off, basestring):
				off = off.rstrip("\0")
			return off
	
	def _ifdread(self, next_ifd):
		ifd = {}
		self._fh.seek(next_ifd)
		count = self._up1("H", self._fh.read(2))
		for i in range(count):
			d = self._fh.read(12)
			tag, type, vc = self._up("HHI", d[:8])
			if type in self.types and self.types[type][0] * vc <= 4:
				tl, fmt = self.types[type]
				d = d[8:8 + (tl * vc)]
				if fmt:
					off = self._up(fmt * vc, d)
				else:
					off = d # ASCII
			else:
				off = self._up1("I", d[8:])
			ifd[tag] = (type, vc, off)
		return ifd

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
		self.activearea = t.ifdget(ifd, 50829)
		exif = t.ifdget(t.ifd[0], 34665)
		if exif:
			t.reinit_from(exif[0])
			exposuretime = t.ifdget(t.ifd[0], 33434)
			if exposuretime:
				self.exposuretime = exposuretime
				self.exposuretime_offset = t.ifd[0][33434][2]
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
