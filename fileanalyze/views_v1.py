from django.shortcuts import render
import zlib
import re

# Create your views here.
from django.http import HttpResponse
import binascii

loopLevel = []
loopStart = []
loopCount = []
loopIndex = []

pngData = b''
fileLoc = 0
htmlString = ""
storedValues = {}
level = 0
instrLoc = 0
dataSize = 0

def is_int(s):
    try: 
        int(s)
        return True
    except ValueError:
        return False

def index(request):
	global htmlString, pngData, fileLoc, storedValues, dataSize, level, instrLoc

	pngFile = open('610110.png', 'rb')
	pngData = pngFile.read()
	fileSize = len(pngData)
	formatFile = open('PNG_Format.txt', 'r')
	instructions = formatFile.readlines()

	instrLen = len(instructions)
	instrLoc = 1

	while True:
		instruction = instructions[instrLoc]
		# htmlString += instruction
		instruction = re.sub(r"[\t]+", "\t", instruction.strip())
		if (instruction == ""):
			continue
		print(str(fileLoc) + ": " + instruction)

		instruction = instruction.split("\t")
		level = instruction[0]
		description = instruction[1]
		dataType = instruction[2]

		if (len(instruction) > 3):
			if(not is_int(instruction[3])):
				# print(storedValues)
				dataSize = int(storedValues[instruction[3]])
			else:
				dataSize = int(instruction[3])
		else:
			dataSize = 0

		if (fileLoc + dataSize > fileSize):
			break

		# if(len(loopLevel) > 0):
		proceed = 0
		while (len(loopLevel) > 0 and level <= loopLevel[-1]):
			proceed = nextLoop()
			if (proceed == 1):
				break
		if (proceed == 1):
			continue

		data = processInstruction(dataType)(dataSize)

		print(description + ": " + data)
		if(data != "_SKIP_"):
			htmlString += description + ": " + data + "<br>"

		fileLoc += dataSize
		if (fileLoc >= fileSize):
			break

		if(len(instruction) > 4):
			if (instruction[4] == "_EXPAND_"):
				dType = "_" + dataType + "_" 
				if (dType in instructions):
					instrLoc = instructions.index(dType)
					doRepeat(1)
			else:
				storedValues[instruction[4]] = data

		instrLoc += 1
		if (instrLoc >= instrLen):
			while (len(loopLevel) > 0):
				if (nextLoop() == 1):
					break
			if (len(loopLevel) == 0):
				break
		
	return HttpResponse(htmlString)

def processInstruction(instr):

	switcher = {
		"HEX": getHex,
		"INT": getInt,
		"CHAR": getChar,
		"_REPEAT_": doRepeat,
		"_SKIP_": getSkip,
		"_END_": getSkip
	}
	return switcher.get(instr, unhandled)

def nextLoop():
	global instrLoc, loopLevel, loopStart, loopCount, loopIndex

	loopIndex[-1] += 1
	if(loopCount[-1] == loopIndex[-1]):
		loopLevel.pop()
		loopStart.pop()
		loopCount.pop()
		loopIndex.pop()
		return 0
	else:
		instrLoc = loopStart[-1]+1
		return 1

def doRepeat(Len):
	global loopLevel, loopStart, loopCount, loopIndex, dataSize
	
	loopLevel.append(level)
	loopStart.append(instrLoc)
	loopCount.append(Len)
	loopIndex.append(0)

	dataSize = 0
	print(dataSize)
	return "_SKIP_"

def getHex(Len):
	return "".join("%02X " % b for b in pngData[fileLoc:fileLoc+Len])

def getChar(Len):
	return pngData[fileLoc:fileLoc+Len].decode("utf-8")

def getInt(Len):
	return str(int.from_bytes(pngData[fileLoc:fileLoc+Len], byteorder='big'))

def getSkip(Len):
	return "_SKIP_"

def unhandled(Len):
	return "Unhlandled Instruction"