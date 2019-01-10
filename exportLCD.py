#!/usr/bin/python

from re import findall

import gimp
from gimpfu import *

gettext.install("gimp20-python", gimp.locale_directory, unicode=True)


class colorConverter:
	def __init__(self, colorMode):
		self.setColorFormat(colorMode)

	def setColorFormat(self, colorMode):
		colorMode = colorMode or ''
		colorMode = colorMode.upper()[::-1]
		self.colorFormat = findall("(\\d{0,2})([ARGBX])", colorMode + " 0X0A0R0G0B0")
		print self.colorFormat
		self.totalBits = {'R': 0, 'G': 0, 'B': 0, 'A': 0, 'X': 0, 'all': 0}
		self.colorBitSequence = []
		for form in self.colorFormat:
			colorName = form[1]
			colorBits = form[0] or 1
			self.totalBits[colorName] += int(colorBits)
			self.totalBits['all'] += int(colorBits)
			self.colorBitSequence += [colorName] * int(colorBits)

		if self.getNumColorBits() > 128:
			raise Exception("Colorformat is larger than 128 bits")

		if self.getNumColorBits() == 0:
			raise Exception("Colorformat results in 0 bit")

		if self.getNumColorBits() % 8 != 0:
			# gprint("Colorformat not byte aligned. Try appropritate X filler")
			raise Exception("Colorformat not byte aligned. Try appropritate X filler")

		self.pixelScaler = {}
		for colorComponent in self.totalBits:
			self.pixelScaler[colorComponent] = ((1 << self.totalBits[colorComponent]) - 1.0) / 255.0

	def getNumColorBits(self):
		return self.totalBits['all']

	def __scale(self, val, component):
		return int(round(val * self.pixelScaler[component]))

	def __unscale(self, val, component):
		return int(round(val / self.pixelScaler[component]))

	def pixelToNumber(self, pixel):
		self.pixelToNumber(rVal=pixel[0], gVal=pixel[1], bVal=pixel[2], aVal=pixel[3])

	def pixelToNumber(self, rVal, gVal, bVal, aVal=0):
		# pixel is a tuple of (R,G,B,A)
		px = {'X': 0, 'R': self.__scale(rVal, 'R'), 'G': self.__scale(gVal, 'G'), 'B': self.__scale(bVal, 'B'), 'A': self.__scale(aVal, 'A')}
		retVal = 0
		for component in self.colorBitSequence:
			retVal = (retVal >> 1) | (0x80000000000000000000000000000000 if (px[component] & 1) > 0 else 0)
			px[component] >>= 1
		return retVal >> (128 - self.totalBits['all'])

	def numberToPixel(self, number):
		# returns (R,G,B,A)
		# TODO: implement
		return (0, 0, 0, 0)


def gprint(txt):
	pdb.gimp_message(txt)


def layerToRAWData(layer, color_converter, minX=0, minY=0, maxX=None, maxY=None):
	retVal = ''
	if maxX is None or maxX > layer.width:
		maxX = layer.width
	if maxY is None or maxY > layer.height:
		maxY = layer.height
	if minX < 0 or minX > maxX:
		minX = 0
	if minY < 0 or minY > maxY:
		minY = 0

	bitPos = 0
	pixels = layer.get_pixel_rgn(minX, minY, maxX, maxY, False, False)
	genOpacityCoef = layer.opacity / 100
	alphaCh = layer.has_alpha
	for y in range(pixels.h):
		gimp.progress_update(float(y) / float(layer.height))
		row = pixels[0:pixels.w, y]
		for x in range(pixels.w):
			pixelR = ord(row[0])
			pixelG = ord(row[1])
			pixelB = ord(row[2])
			if alphaCh:
				pixelA = ord(row(3) * genOpacityCoef)
				row = row[4:]
			else:
				pixelA = 0
				row = row[3:]
			DDpixel = color_converter.pixelToNumber(rVal=pixelR, gVal=pixelG, bVal=pixelB, aVal=pixelA)
			for i in range(color_converter.getNumColorBits() / 8):
				retVal = retVal + '%c' % (DDpixel & 0xFF)
				DDpixel = DDpixel >> 8
	return retVal


def newFlatImage(fromImage):
	# copyName = gimp.pdb.gimp_edit_named_copy_visible(fromImage, "FlatGUI")
	# newImage=gimp.pdb.gimp_edit_named_paste_as_new(copyName)
	newImage = pdb.gimp_image_duplicate(fromImage)
	pdb.gimp_image_flatten(newImage)
	newImage.active_layer.name = fromImage.name
	pdb.gimp_image_clean_all(newImage)
	return newImage


def save_lcd(img, drawable, filename, raw_filename, source, colorformat):
	gprint('0')
	gprint(filename)
	gprint(raw_filename)
	flatimage = newFlatImage(img)
	gprint('1')
	col_conv = colorConverter(colorformat)
	gprint('2')
	raw_layer = layerToRAWData(flatimage.active_layer, col_conv)
	gprint('3')
	gimp.delete(flatimage)
	gprint('4')
	with open(filename, 'wb') as fout:
		fout.write(raw_layer)


def register_save_handlers():
	gimp.register_save_handler('file-rawlcd-save', 'lcd', '')


register(
		"file-rawlcd-save",
		N_("Save as RAW LCD pixels"),
		"Saves the image in RAW LCD format (.lcd)",
		"Attila K.",
		"Attila K.",
		"2019",
		N_("Flexible Raw LCD format"),
		"RGB*",
		[  # input args. Format (type, name, description, default [, extra])
			(PF_IMAGE, "image", "Input image", None),
			(PF_DRAWABLE, "drawable", "Input drawable", None),
			(PF_STRING, "filename", "The name of the file", None),
			(PF_STRING, "raw-filename", "The name of the file", None),
			(PF_STRING, "source", _("Character _source"), None),
			(PF_STRING, "colorformat", "Color format [ARGBX]", "R5G6B5"),
		],
		[],
		save_lcd,
		on_query=register_save_handlers,
		menu='<Save>', domain=("gimp20-python", gimp.locale_directory)
)

main()
