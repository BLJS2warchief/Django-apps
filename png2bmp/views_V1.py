from django.shortcuts import render
from django.http import HttpResponse
import zlib
import sys
import math
from PIL import Image
import numpy as np
import os

def PaethPredictor(a, b, c):
    # ; a = left, b = above, c = upper left
    if (b == 0 and c == 0):
        return a
    p = a + b - c        # initial estimate
    pa = abs(p - a)      # distances to a, b, c
    pb = abs(p - b)
    pc = abs(p - c)
    # ; return nearest of a,b,c,
    # ; breaking ties in order a,b,c.
    if(pa <= pb and pa <= pc):
        return a
    elif(pb <= pc):
        return b
    else:
        return c

def index(request):
	if (request.GET.get("inFile") is not None):
		inFile = request.GET.get("inFile")
	else:
		return "Please specify an input file"
		
	if (request.GET.get("debug") is not None):
		ifDebug = True
	else:
		ifDebug = False

	fPath = "../../png2bmp/"
	if os.path.exists(fPath + inFile + '.png'):
		pngFile = open(fPath + inFile + '.png', 'rb')
	else:
		return HttpResponse("File not found")

	pngData = pngFile.read()

	pngInterlace = pngData[28:29]
	if (pngInterlace != b'\x00'):
		print("Interlace method not supported ", pngInterlace)
		pngFile.close()
		return HttpResponse("Interlace method not supported " + str(pngInterlace))
	pngBitDepth = pngData[24:25]
	if (pngBitDepth != b'\x08'):
		print("Bit Depth not supported ", pngBitDepth)
		pngFile.close()
		return HttpResponse("Bit Depth not supported " + str(pngBitDepth))

	bmpFile = open(fPath + inFile + '.bmp', 'wb')
	pngWidth = pngData[16:20]
	pngWidthInt = int.from_bytes(pngWidth, byteorder='big')
	pngHeight = pngData[20:24]
	pngHeightInt = int.from_bytes(pngHeight, byteorder='big')

	pngColorType = pngData[25:26]
	pngColorTypeInt = int.from_bytes(pngColorType, byteorder='big')

	alphaFlag = False

	if (pngColorTypeInt == 0):
		rgbA = 1
		bmpRGBA = 1
	elif (pngColorTypeInt == 2):
		rgbA = 3
		bmpRGBA = 3
	elif (pngColorTypeInt == 3):
		rgbA = 3
		bmpRGBA = 3
	elif (pngColorTypeInt == 4):
		rgbA = 2
		bmpRGBA = 1
		alphaFlag = True
	elif (pngColorTypeInt == 6):
		rgbA = 4
		bmpRGBA = 3
		alphaFlag = True

	bmpWidth = pngWidthInt.to_bytes(4, byteorder='little')
	bmpHeight = pngHeightInt.to_bytes(4, byteorder='little')

	print(pngWidthInt)
	print(pngHeightInt)

	bmpOffset = b'\x36\x00\x00\x00'
	# if (bmpRGBA > 1):			#### grayscale / RGB
	# 	bmpSize = 14 + 40 + 3 * (pngWidthInt * pngHeightInt)
	# else:
		# bmpSize = 14 + 40 + 1 * (pngWidthInt * pngHeightInt)
	bmpSize = 14 + 40 + 3 * (pngWidthInt * pngHeightInt)
	bmpSize = bmpSize.to_bytes(4, byteorder='little')

	bmpData = bytearray(b'\x42\x4D' + bmpSize + b'\x00\x00\x00\x00' + bmpOffset + b'\x28\x00\x00\x00')
	bmpData += bmpWidth + bmpHeight + b'\x01\x00'
	# if (bmpRGBA > 1):			#### grayscale / RGB
	# 	bmpData += b'\x18\x00'
	# else:
	# 	bmpData += b'\x08\x00'
	bmpData += b'\x18\x00'
	bmpData += b'\x00\x00\x00\x00' + b'\x00\x00\x00\x00'
	bmpData += b'\x00\x00\x00\x00' + b'\x00\x00\x00\x00' + b'\x00\x00\x00\x00' + b'\x00\x00\x00\x00'
	bmpHeaderSize = len(bmpData)
	#PNG chunk ==> 4-byte size ;; 4-byte type ;;  data ;; 4-byte CRC


	idatData = b''
	fileLoc = 8
	fileSize = len(pngData)
	plteR = []
	plteG = []
	plteB = []
	knownFilters = [0,1,2,3,4]
	valBkgdR = 255
	valBkgdG = 255
	valBkgdB = 255
	chrm = [[0 for x in range(3)] for y in range(3)]
	chrmW = [0 for x in range(3)]
	M = np.array(chrm)
	Minv = np.array(chrm)
	# chrm = [[]]
	plteFlag = False
	gammaFlag = False
	chrmFlag = False

	while(fileLoc < fileSize):
		sizeChunk = int.from_bytes(pngData[fileLoc:fileLoc+4], byteorder='big')
		#sizeChunk is only Data size ;; chunk = size + type + data_size + crc
		typeChunk = pngData[fileLoc+4:fileLoc+8].decode('ascii')

		print(str(sizeChunk) + typeChunk)
		fileTempLoc = fileLoc + 8
		if (typeChunk == 'PLTE'):
			plteFlag = True
			for i in range(0, sizeChunk//3):
				plteR.append(pngData[fileTempLoc:fileTempLoc+1])
				plteG.append(pngData[fileTempLoc+1:fileTempLoc+2])
				plteB.append(pngData[fileTempLoc+2:fileTempLoc+3])
				fileTempLoc += 3
		elif (typeChunk == 'bKGD'):
			if (pngColorTypeInt in [2, 6]):
				valBkgdR = int.from_bytes(pngData[fileLoc+9:fileLoc+10], byteorder='big')
				valBkgdG = int.from_bytes(pngData[fileLoc+11:fileLoc+12], byteorder='big')
				valBkgdB = int.from_bytes(pngData[fileLoc+13:fileLoc+14], byteorder='big')
			elif (pngColorTypeInt in [0, 4]):
				valBkgdR = int.from_bytes(pngData[fileLoc+9:fileLoc+10], byteorder='big')
			elif (pngColorTypeInt == 3):
				idx = int.from_bytes(pngData[fileLoc+9:fileLoc+10], byteorder='big')
				valBkgdR = int.from_bytes(plteR[idx])
				valBkgdG = int.from_bytes(plteG[idx])
				valBkgdB = int.from_bytes(plteB[idx])
			# valBkgdR = 255
			print(valBkgdR, valBkgdG, valBkgdB)
		elif (typeChunk == 'gAMA'):
			invGamma = 100000.0/int.from_bytes(pngData[fileTempLoc:fileTempLoc+sizeChunk], byteorder='big')
			# invGamma = 1.0/gamma		### ABOVE IS ALREADY INV
			# invGamma = 50
			gammaRGB = []
			for i in range(256):
				gammaRGB.append((int( ((i/255.0) ** invGamma) * 255)%256).to_bytes(1, byteorder="big"))
			# if (ifDebug):
			# 	print(gammaRGB)
			gammaFlag = True
			print("Gamma = ", invGamma)
		elif (typeChunk == 'cHRM'):
			chrmW[0] = int.from_bytes(pngData[fileLoc+8:fileLoc+12], byteorder='big')/100000
			chrmW[1] = int.from_bytes(pngData[fileLoc+12:fileLoc+16], byteorder='big')/100000
			chrm[0][0] = int.from_bytes(pngData[fileLoc+16:fileLoc+20], byteorder='big')/100000
			chrm[1][0] = int.from_bytes(pngData[fileLoc+20:fileLoc+24], byteorder='big')/100000
			chrm[0][1] = int.from_bytes(pngData[fileLoc+24:fileLoc+28], byteorder='big')/100000
			chrm[1][1] = int.from_bytes(pngData[fileLoc+28:fileLoc+32], byteorder='big')/100000
			chrm[0][2] = int.from_bytes(pngData[fileLoc+32:fileLoc+36], byteorder='big')/100000
			chrm[1][2] = int.from_bytes(pngData[fileLoc+36:fileLoc+40], byteorder='big')/100000

			print("White Point x: " + str(chrmW[0]))
			print("White Point y: " + str(chrmW[1]))
			print("Red x: " + str(chrm[0][0]))
			print("Red y: " + str(chrm[1][0]))
			print("Green x: " + str(chrm[0][1]))
			print("Green y: " + str(chrm[1][1]))
			print("Blue x: " + str(chrm[0][2]))
			print("Blue y: " + str(chrm[1][2]))

			for i in range(3):
				chrm[2][i] = 1 - chrm[0][i] - chrm[1][i]

			chrmW[2] = 1 - chrmW[0] - chrmW[1]
			# chrmW = [1, 1, 1]							#### NO EFFECT CHRM VALUES
			# chrm = [[1, 0, 0], [0, 1, 0], [0, 0, 1]]	#### NO EFFECT CHRM VALUES

			chrm = np.array(chrm)
			if (ifDebug):
				print("chrm", chrm)
			if (ifDebug):
				print("chrmW", chrmW)
			yLuminance = chrmW[1]
			for i in range(3):
				chrmW[i] /= yLuminance
			
			if (ifDebug):
				print("chrmW/Wy", chrmW)

			invCHRM = np.linalg.inv(chrm)
			if (ifDebug):
				print("invCHRM", invCHRM)
			chrmXYZ = np.matmul(invCHRM, [[chrmW[0]], [chrmW[1]], [chrmW[2]]])
			if (ifDebug):
				print("chrmXYZ = invCHRM * chrmW", chrmXYZ)
			M = np.matmul(chrm,[[chrmXYZ[0][0], 0, 0], [0, chrmXYZ[1][0], 0], [0, 0, chrmXYZ[2][0]]])
			if (ifDebug):
				print("M", M)
			Minv = np.linalg.inv(M)
			Minv = np.where(Minv<0.0, 0.0, Minv)
			Minv = np.where(Minv>1.0, 1.0, Minv)
			# M = np.array(chrm[])
			# Minv = np.linalg.inv(M)

			if (ifDebug):
				print("Minv", Minv)
			chrmFlag = True
		elif (typeChunk == 'IDAT'):
			idatData += pngData[fileLoc+8:fileLoc+8+sizeChunk]
		fileLoc += sizeChunk + 12

	#Uncompress data
	zlibData = zlib.decompress(idatData)
	zlibDataSize = len(zlibData)
	# zlibDataLoc = zlibDataSize

	#Un Filter the data


	#Add to BMP
	zlibData = bytearray(zlibData)

	if (request.GET.get("dat") is not None):
		datFile = open(fPath + inFile+'.dat', 'wb')
		datFile.write(zlibData)
		datFile.close()

	if (request.GET.get("gamma") is not None):
		gammaFlag = False

	if (request.GET.get("chrm") is not None):
		chrmFlag = False

	if (request.GET.get("alpha") is not None):
		alphaFlag = False

	zlibPrevLoc = 0
	zlibDataLoc = 0
	rawBytesPrev = bytearray(b'\x00' * rgbA * (pngWidthInt+2))
	rawBytesPrior = bytearray(b'\x00' * rgbA * (pngWidthInt+2))
	pixelRGB = [0 for x in range(3)]		#### 3 needed for Matrix multiplication....

	typeFilterPrev = ""

	scanlineCount = 0
	debugPixels = pngWidthInt // 10

	bmpImageData = bytearray(b'')
	while(zlibPrevLoc < zlibDataSize):
		if (plteFlag):
			zlibDataLoc += pngWidthInt+1
		else:
			zlibDataLoc += (pngWidthInt*rgbA)+1

		zlibScanLine = zlibData[zlibPrevLoc:zlibDataLoc]
		typeFilter = zlibScanLine[0]
		print(str(typeFilter),end='',flush=True)
		bmpImageRow = bytearray(b'')
		rawBytes = bytearray(b'\x00\x00\x00\x00')
		i = 0

		while (i < pngWidthInt):
			if (typeFilter not in knownFilters):
				print("?", end='')
				break

			if (plteFlag):
				valR = plteR[zlibScanLine[i+1]]
				if (rgbA > 2):
					valG = plteG[zlibScanLine[i+1]]
					valB = plteB[zlibScanLine[i+1]]
				if (alphaFlag):
					valA = plteB[zlibScanLine[i+1]]		#### pltA_______
				i += 1
			else:
				valR = zlibScanLine[i*rgbA+1:i*rgbA+2]
				if (rgbA > 2):
					valG = zlibScanLine[i*rgbA+2:i*rgbA+3]
					valB = zlibScanLine[i*rgbA+3:i*rgbA+4]
				if (alphaFlag):
					valA = bytes(zlibScanLine[i*rgbA+4:i*rgbA+5])
				i += 1
			if (typeFilter == 1):
				rawBytes[0] = (int.from_bytes(valR, byteorder='big') + rawBytes[0])%256
				rawBytesPrev[i*rgbA] = rawBytes[0]
				valR = rawBytes[0].to_bytes(1, byteorder='little')

				if (rgbA > 2):
					rawBytes[1] = (int.from_bytes(valG, byteorder='big') + rawBytes[1])%256
					rawBytesPrev[i*rgbA+1] = rawBytes[1]
					valG = rawBytes[1].to_bytes(1, byteorder='little')

					rawBytes[2] = (int.from_bytes(valB, byteorder='big') + rawBytes[2])%256
					rawBytesPrev[i*rgbA+2] = rawBytes[2]
					valB = rawBytes[2].to_bytes(1, byteorder='little')
				if (alphaFlag):
					rawBytes[3] = (int.from_bytes(valA, byteorder='big') + rawBytes[3])%256
					rawBytesPrev[i*rgbA+3] = rawBytes[3]
					valA = rawBytes[3].to_bytes(1, byteorder='little')
			elif (typeFilter == 2):
				rawBytes[0] = (int.from_bytes(valR, byteorder='big') + rawBytesPrior[i*rgbA])%256
				rawBytesPrev[i*rgbA] = rawBytes[0]
				valR = rawBytes[0].to_bytes(1, byteorder='little')

				if (rgbA > 2):
					rawBytes[1] = (int.from_bytes(valG, byteorder='big') + rawBytesPrior[i*rgbA+1])%256
					rawBytesPrev[i*rgbA+1] = rawBytes[1]
					valG = rawBytes[1].to_bytes(1, byteorder='little')

					rawBytes[2] = (int.from_bytes(valB, byteorder='big') + rawBytesPrior[i*rgbA+2])%256
					rawBytesPrev[i*rgbA+2] = rawBytes[2]
					valB = rawBytes[2].to_bytes(1, byteorder='little')
				if (alphaFlag):
					rawBytes[3] = (int.from_bytes(valA, byteorder='big') + rawBytesPrior[i*rgbA+3])%256
					rawBytesPrev[i*rgbA+3] = rawBytes[3]
					valA = rawBytes[3].to_bytes(1, byteorder='little')
			elif (typeFilter == 3):
				rawBytes[0] = (int.from_bytes(valR, byteorder='big') + math.floor((rawBytes[0] + rawBytesPrior[i*rgbA])/2))%256
				rawBytesPrev[i*rgbA] = rawBytes[0]
				valR = rawBytes[0].to_bytes(1, byteorder='little')

				if (rgbA > 2):
					rawBytes[1] = (int.from_bytes(valG, byteorder='big') + math.floor((rawBytes[1] + rawBytesPrior[i*rgbA+1])/2))%256
					rawBytesPrev[i*rgbA+1] = rawBytes[1]
					valG = rawBytes[1].to_bytes(1, byteorder='little')

					rawBytes[2] = (int.from_bytes(valB, byteorder='big') + math.floor((rawBytes[2] + rawBytesPrior[i*rgbA+2])/2))%256
					rawBytesPrev[i*rgbA+2] = rawBytes[2]
					valB = rawBytes[2].to_bytes(1, byteorder='little')
				if (alphaFlag):
					rawBytes[3] = (int.from_bytes(valA, byteorder='big') + math.floor((rawBytes[3] + rawBytesPrior[i*rgbA+3])/2))%256
					rawBytesPrev[i*rgbA+3] = rawBytes[3]
					valA = rawBytes[3].to_bytes(1, byteorder='little')
			elif (typeFilter == 4):
				rawBytes[0] = (int.from_bytes(valR, byteorder='big') + PaethPredictor(rawBytes[0], rawBytesPrior[i*rgbA], rawBytesPrior[i*rgbA-rgbA]))%256
				rawBytesPrev[i*rgbA] = rawBytes[0]
				valR = rawBytes[0].to_bytes(1, byteorder='little')

				if (rgbA > 2):
					rawBytes[1] = (int.from_bytes(valG, byteorder='big') + PaethPredictor(rawBytes[1], rawBytesPrior[i*rgbA+1], rawBytesPrior[i*rgbA-rgbA+1]))%256
					rawBytesPrev[i*rgbA+1] = rawBytes[1]
					valG = rawBytes[1].to_bytes(1, byteorder='little')

					rawBytes[2] = (int.from_bytes(valB, byteorder='big') + PaethPredictor(rawBytes[2], rawBytesPrior[i*rgbA+2], rawBytesPrior[i*rgbA-rgbA+2]))%256
					rawBytesPrev[i*rgbA+2] = rawBytes[2]
					valB = rawBytes[2].to_bytes(1, byteorder='little')
				if (alphaFlag):
					rawBytes[3] = (int.from_bytes(valA, byteorder='big') + PaethPredictor(rawBytes[3], rawBytesPrior[i*rgbA+3], rawBytesPrior[i*rgbA-rgbA+3]))%256
					rawBytesPrev[i*rgbA+3] = rawBytes[3]
					valA = rawBytes[3].to_bytes(1, byteorder='little')

			# print(valR, valG, valB, end='=')
			if (gammaFlag):
				pixelRGB[0] = int.from_bytes(valR, byteorder='big')
				valR = gammaRGB[pixelRGB[0]]
				if (rgbA > 2):
					pixelRGB[1] = int.from_bytes(valG, byteorder='big')
					pixelRGB[2] = int.from_bytes(valB, byteorder='big')
					valG = gammaRGB[pixelRGB[1]]
					valB = gammaRGB[pixelRGB[2]]


			if (chrmFlag):			#### No CHRM for color type grayscale ?????????
				pixelRGB[0] = int.from_bytes(valR, byteorder='big')
				pixelRGB[1] = int.from_bytes(valG, byteorder='big')
				pixelRGB[2] = int.from_bytes(valB, byteorder='big')

				pixelRGB = np.matmul(pixelRGB, Minv)
				pixelRGB = np.where(pixelRGB > 255, 255, pixelRGB)
				pixelRGB = np.where(pixelRGB < 0, 0, pixelRGB)
				pixelRGB = pixelRGB.tolist()
				pixelRGB = [int(x) for x in pixelRGB]

				valR = pixelRGB[0].to_bytes(1, byteorder='big')
				valG = pixelRGB[1].to_bytes(1, byteorder='big')
				valB = pixelRGB[2].to_bytes(1, byteorder='big')
				
			if (alphaFlag):
				pixelRGB[0] = int.from_bytes(valR, byteorder='big')
				if (rgbA > 2):
					pixelRGB[1] = int.from_bytes(valG, byteorder='big')
					pixelRGB[2] = int.from_bytes(valB, byteorder='big')
				pixelAlpha = int.from_bytes(valA, byteorder='big')

				pixelRGB[0] = int(pixelAlpha/255 * pixelRGB[0] + (1 - pixelAlpha/255) * valBkgdR)
				valR = pixelRGB[0].to_bytes(1, byteorder='big')
				if (rgbA > 2):
					pixelRGB[1] = int(pixelAlpha/255 * pixelRGB[1] + (1 - pixelAlpha/255) * valBkgdG)
					pixelRGB[2] = int(pixelAlpha/255 * pixelRGB[2] + (1 - pixelAlpha/255) * valBkgdB)
					valG = pixelRGB[1].to_bytes(1, byteorder='big')
					valB = pixelRGB[2].to_bytes(1, byteorder='big')

			if (ifDebug and i < debugPixels):
				if (typeFilter == 0):		#___
					valR = b'\x00'
					if (rgbA > 2):
						valG = b'\xFF'
						valB = b'\xFF'
				elif (typeFilter == 1):		#YELLOW
					valR = b'\xFF'
					if (rgbA > 2):
						valG = b'\xFF'
						valB = b'\x00'
				elif (typeFilter == 2):		#BLUE___
					valR = b'\x00'
					if (rgbA > 2):
						valG = b'\x00'
						valB = b'\xFF'
				elif (typeFilter == 3):		#GREEN___
					valR = b'\x00'
					if (rgbA > 2):
						valG = b'\xFF'
						valB = b'\x00'
				elif (typeFilter == 4):		#RED___
					valR = b'\xFF'
					if (rgbA > 2):
						valG = b'\x00'
						valB = b'\x00'
			# print(valR, valG, valB, end='; ')
			if (rgbA > 2):
				bmpImageRow += valB + valG
			else:
				bmpImageRow += valR + valR
			bmpImageRow += valR
			
		i = pngWidthInt * bmpRGBA		##### adjust for 4-BYTE BOUNDARY________
		while (i%4 != 0):		
			bmpImageRow += b'\x00'
			print("_", end='')
			i += 1

### BMP Pixel Data ===>		7 8 9 . . .		=> Row 2
###							1 2 3 4 5 6		=> Row 1
		# print(len(bmpImageRow), end='')
		bmpImageData = bmpImageRow + bmpImageData
		rawBytesPrior = rawBytesPrev.copy()
		zlibPrevLoc = zlibDataLoc
		print('.',end='',flush=True)
		if (ifDebug):
			print()
		scanlineCount += 1
		# if (scanlineCount == 20):
		#     break

	bmpFile.write(bmpData + bmpImageData)
	pngFile.close()
	bmpFile.close()

	content = Image.open(fPath + inFile + ".bmp")
	response = HttpResponse(content_type='image/bmp')
	content.save(response, "bmp")
	return response
