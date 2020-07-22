from django.shortcuts import render
import zlib
import re

# Create your views here.
from django.http import HttpResponse
import binascii

def init():
	global fileData, fileLoc, htmlString, storedValues, level, instrLoc, dataSize
	global instructions, instrBlocks, currentBlock, description
	global loopCount, loopIndex, loopLevel, loopStart, loopBlock

	fileData = b''
	fileLoc = 0
	htmlString = ""
	storedValues = {}
	level = 0
	instrLoc = 0
	dataSize = 0
	instructions = []
	instrBlocks = {}
	currentBlock = ""
	description = ""
	loopLevel = []
	loopStart = []
	loopCount = []
	loopIndex = []
	loopBlock = []

def isInt(s):
    try: 
        int(s)
        return True
    except ValueError:
        return False

def index(request):
	global htmlString, fileData, fileLoc, storedValues, dataSize, level, description
	global instrLoc, instructions, currentBlock

	init()
	expandReturn = []

	if (request.GET.get("inFile") is not None):
		inFile = request.GET.get("inFile")
	else:
		return HttpResponse("Please specify an input file")
	
	fPath = '../../png2bmp/'

	dataFile = open(fPath + inFile, 'rb')
	fileData = dataFile.read()
	fileSize = len(fileData)
	
	if (request.GET.get("format") is not None):
		formatFile = request.GET.get("format").upper()  + "_Format.txt"
	else:
		return HttpResponse("Please specify input file type [png, bmp ...]")
	
	formatFile = open(formatFile, 'r')
	instructions = formatFile.readlines()

	instrLen = len(instructions)
	parseInstructions()

	instrLoc = 1
	while True:
		if (instrLoc < 0):		# when _END_ of _MAIN_ is reached....
			break

		instruction = instructions[instrLoc]
		# htmlString += instruction
		instruction = re.sub(r"[\t]+", "\t", instruction.strip())
		if (instruction == ""):
			continue
		print(str(fileLoc) + ": " + instruction)

		instruction = instruction.split("\t")
		level = instruction[0]
		description = instruction[1]

		dataSize = 0
		
		if(level == '000'):
			if (description != "_END_"):
				currentBlock = description
				if (description == "_MAIN_"):
					data = handleRepeat(1, -2)
				else:
					data = handleRepeat(1, instrLoc)
				instrLoc += 1
			else:
				# while (len(loopLevel) > 0):
				print(currentBlock)
				print(loopBlock)	
				while (len(loopLevel) > 0 and loopBlock[-1] == currentBlock):
					print(currentBlock)
					print(loopBlock)
					print(loopStart)
					
					proceed = nextLoop()
					if (proceed == 1):
						break
				
				if (proceed == 0):
					if(len(expandReturn) > 0):
						instrLoc = expandReturn[-1]+1
						expandReturn.pop()
						if (len(loopBlock) > 0):
							currentBlock = loopBlock[-1]
					else:
						break
			
			continue


		dataType = instruction[2]

		if (len(instruction) > 3):
			if(not isInt(instruction[3])):
				print(storedValues)
				dataSize = int(storedValues[instruction[3]])
			else:
				dataSize = int(instruction[3])

		if (fileLoc + dataSize > fileSize):
			break

		# handle _REPEAT_ endings.... 110 -> 100
		proceed = 0
		while (len(loopLevel) > 0 and currentBlock == loopBlock[-1] and level <= loopLevel[-1]):
			proceed = nextLoop()
			if (proceed == 1):
				break
		# If block change (or) level change .....
		# if (proceed == 1):
		# 	continue

		data = processInstruction(dataType)(dataSize)

		print(description, ": ", data)
		if(data != "_SKIP_"):
			htmlString += str(fileLoc) + " :: " + description + ": " + data + "<br>"

		fileLoc += dataSize
		if (fileLoc >= fileSize):
			break

		if(len(instruction) > 4):
			if (instruction[4] == "_EXPANDNEXT_"):
				block = "_" + data + "_"
				if(block in instrBlocks.keys()):
					# If _EXPANDNEXT_ is found; skip the next instruction_______
					expandReturn.append(instrLoc+1)
					instrLoc = instrBlocks[block]
					continue
			else:
				storedValues[instruction[4]] = data

		instrLoc += 1
		
	return HttpResponse(htmlString)

def parseInstructions():
	global instrBlocks
	
	i = 0
	while(i < len(instructions)-1):
		i += 1
		instruction = instructions[i]
		instruction = re.sub(r"[\t]+", "\t", instruction.strip())
		if (instruction == ""):
			continue
		# print(str(fileLoc) + ": " + instruction)

		instruction = instruction.split("\t")
		if(instruction[0] == '000' and instruction[1] != "_END_"):
			instrBlocks[instruction[1]] = i
		else:
			continue
	print(instrBlocks)

def processInstruction(instr):

	switcher = {
		"HEX": getHex,
		"INT": getInt,
		"LINT": getLInt,
		"CHAR": getChar,
		"_REPEAT_": doRepeat,
		"_SKIP_": getSkip,
		"_END_": getSkip
	}
	return switcher.get(instr, unhandled)

def nextLoop():
	global instrLoc, loopLevel, loopStart, loopCount, loopIndex

	loopIndex[-1] += 1
	print("nextLoop ", loopCount[-1], ", ", loopIndex[-1])
	if(loopCount[-1] == loopIndex[-1]):
		loopLevel.pop()
		loopStart.pop()
		loopCount.pop()
		loopIndex.pop()
		loopBlock.pop()
		return 0
	else:
		instrLoc = loopStart[-1]+1
		return 1

def doRepeat(Len):
	handleRepeat(Len, instrLoc)
	return "_SKIP_"

def handleRepeat(Len, Loc):
	global loopLevel, loopStart, loopCount, loopIndex, dataSize
	
	loopLevel.append(level)
	loopStart.append(Loc)
	loopCount.append(Len)
	loopIndex.append(0)
	loopBlock.append(currentBlock)

	print(dataSize)
	dataSize = 0
	return

def getHex(Len):
	return "".join("%02X " % b for b in fileData[fileLoc:fileLoc+Len])

def getChar(Len):
	return fileData[fileLoc:fileLoc+Len].decode("utf-8")

def getInt(Len):
	return str(int.from_bytes(fileData[fileLoc:fileLoc+Len], byteorder='big'))

def getLInt(Len):
	return str(int.from_bytes(fileData[fileLoc:fileLoc+Len], byteorder='little'))

def getSkip(Len):
	return "_SKIP_"

def unhandled(Len):
	return "Unhlandled Instruction"