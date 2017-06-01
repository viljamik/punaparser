#!/usr/bin/python
# -*- coding: utf-8 -*-
# https://stackoverflow.com/questions/13437727/python-write-to-excel-spreadsheet
#
import struct
import os
import sys
import gzip
import re

reload(sys)  
sys.setdefaultencoding('utf8')

if (len(sys.argv) < 2):
	print "Usage: ./parse.py filename.tsr ... "
	sys.exit()

#FILE_NAME = "video"
#FILE_NAME = "server"
#FILE_NAME = "client"

team_1_score = 0
team_2_score = 0

is_server_video = False

players_have_teams = False

# All players for all videos
all_players = {}

# Players for single video
players = {}


class Player(object):
    name = ""
    index = -1
    team = -1
    
    games_played = 0
    wins = 0
    losses = 0
    total_goals = 0
    total_assists = 0

    def __init__(self, name):
        self.name = name
        #print name

    def win_percentage(self):
    	if self.games_played == 0:
    		return 100.0
    	else:
    		return float(self.wins) / float(self.games_played) * 100.0

    def goals_per_game(self):
    	if self.games_played == 0:
    		return 0
    	else:
    		return float(self.total_goals) / float(self.games_played)

    def assists_per_game(self):
    	if self.games_played == 0:
    		return 0
    	else:
    		return float(self.total_assists) / float(self.games_played)

    def dump_stats(self):
    	print self.name + ":"
    	print "games played: " + str(self.games_played)
    	print "wins: " + str(self.wins)
    	print "losses: " + str(self.losses)
    	print "win percentage: %.0f%%" % self.win_percentage()
    	print "goals: " + str(self.total_goals)
    	print "goals per game: %.1f" % self.goals_per_game()
    	print "assists: " + str(self.total_assists)
    	print "assists per game: %.1f" % self.assists_per_game()

def printAsHex(data):
	print(':'.join(x.encode('hex') for x in data))

def readByte(data, index):
	return struct.unpack('>b', data[index:index+1])[0]

def readShort(data, index):
	return struct.unpack('>h', data[index:index+2])[0]

def readInteger(data, index):
	return struct.unpack('>I', data[index:index+4])[0]

def readFloat(data, index):
	return struct.unpack('>f', data[index:index+4])[0]

def playerByIndex(player_index):
	for player in players.values():
		if player.index == player_index:
			return player
	return 0

def fileSize(filename):
    st = os.stat(filename)
    return st.st_size

def createPlayer(data, player_index):
	index = 0
	hash = readInteger(data, index)
	index += 4

	#int primary_color: 3 bytes
    #int secondary_color: 3 bytes
    #int tertiary_color: 3 bytes
	index += 9

	#bool is_ghost: 1 byte
	index += 1

	#int color_style: 1 byte
	index += 1

	player_name = str(data[index:index+17])
	player_name = player_name.strip()
	player_name = player_name.strip("\0")

	#print "player_name: " + player_name

	if (player_name in all_players.keys()):
		#print "player " + player_name + " already exists"
		player = all_players[player_name]
	else:
		#print "creating player " + str(player_index) + " : " + player_name 
		player = Player(player_name)
		all_players[player_name] = player

	players[player_name] = player

	player.index = player_index

	#print player

def handleFileHeader(length, data):
	video_file_type = readShort(data, 0)
	#print hex(video_file_type)
	global is_server_video
	if video_file_type == 0x07b8:
		is_server_video = True
	else:
		is_server_video = False
	#print "is_server_video: " + str(is_server_video)

def handleHeader(length, header):
	#print "header"

	header_length = len(str(header))

	#print "header len: " + str(header_length)

	if header_length < 26:
		return

	lap_number = readShort(header, 0) 
	track_data_length = readInteger(header, 2)
	track_hash = header[6:6+16]
	track_name_length = readInteger(header, 22)

	#print lap_number
	#print track_data_length
	#print track_hash
	#print track_name_length
	track_name = str(header[26:26+track_name_length])
	#print "track_name: " + track_name

	index = 26 + track_name_length

	track_maker_length = readInteger(header, index)
	index += 4

	track_maker = str(header[index:index+track_maker_length])
	#print "track_maker " + str(track_maker)
	index += track_maker_length

	# player_data_length: 4 bytes
	player_data_length = readInteger(header, index)
	index += 4

	# version: 4 bytes
	version = readInteger(header, index)
	index += 4

	# player_count: 4 bytes
	player_count = readInteger(header, index)
	index += 4
	#print "player_count: " + str(player_count) 

	# unknown: 12 bytes
	index = index + 12

	# Last player is "PunaBall"
	for i in range(player_count - 1):
		#print "i"+str(i)
		createPlayer(header[index:index+32], i)
		index += 32

def handleScore(new_score_1, new_score_2, player, assistee):
	global team_1_score
	global team_2_score

	if (team_1_score != new_score_1):
		team_1_score = new_score_1
	elif team_2_score != new_score_2:
		team_2_score = new_score_2

	if player:
		player.total_goals += 1

	if assistee:
		assistee.total_assists += 1

def handleFinalScore(team_1_score, team_2_score):
	#print "team_1_score = " + str(team_1_score)
	#print "team_2_score = " + str(team_2_score)

	if (team_1_score > team_2_score):
		winning_team = 0
	elif (team_2_score > team_1_score):
		winning_team = 1
	else: # DRAW
		winning_team = 2

	for player in players.values():
		player.games_played += 1

		if winning_team != 2:
			if (player.team == winning_team):
				player.wins += 1
			else:
				player.losses += 1

def handleChat(length, data):
	msg = str(data[4:length - 5])

	msg = str(msg.strip()).decode('Cp1252')

	#msg = msg.decode('unicode_escape').encode('utf8')


	#print (msg[0:10])
	#if msg.startswith("Final score:"):
	if msg.startswith("Final score:"):
		splitted = msg.split(" ")
		if len(splitted) == 5:
			team_1_score = int(splitted[2].split("-")[0])
			team_2_score = int(splitted[2].split("-")[1])
			handleFinalScore(team_1_score, team_2_score)

	# Goal
	pattern = re.compile("^[0-9]+-[0-9]*")
	if (pattern.match(msg)):
		scores = re.findall(r'\d+', msg)
		new_score_1 = int(scores[0])
		new_score_2 = int(scores[1])
		parts = msg.split(" ")
		if len(parts) > 1:
			player_name = str(parts[1])

			player = None
			if player_name in all_players.keys():
				player = all_players[player_name]

			assistee = None
			if (len(parts) > 2):
				assistee_name = (parts[2])[1:-1]
				if assistee_name in all_players.keys():
					assistee = all_players[assistee_name]

			if player:
				handleScore(new_score_1, new_score_2, player, assistee)

		#print "goal for player: " + player.name
	else:
		pass

	#print "chat message: " + msg

# Sets correct team using player's x coordinate
def setTeam(player, player_x, player_y):
	limit = 300
	if (player_x < limit):
		player.team = 0
	else:
		player.team = 1
	#print "set team for " + player.name + ":" + str(player.team)

def handleRaceState(length, data):

	#print "race stat len: " + str(length)

	player_count = 1#len(players)


	index = 0

	#identifier = struct.unpack('>I', data[index:index+4])[0]
	#index = index + 4
	#print "identifier:" + str(identifier)

	statcount = struct.unpack('b', data[19:20])[0]
	#print "statcount:" + str(statcount) 

	racetime = readInteger(data, 0)
	index = index + 4
	#print "racetime: " + str(racetime)

	global is_server_video
	global players_have_teams

	if is_server_video:
		race_stat_size = 32
		start_byte = 20
	else:
		race_stat_size = 14
		start_byte = 20

	for i in range(statcount):

		index = race_stat_size * (i) + start_byte
		#print "index:" + str(index)

		#if not is_server_video:
			#index += 3 # angle first

		if is_server_video:
			player_x = readFloat(data, index) #struct.unpack('>f', data[index:index+4])[0]
			index += 4

			player_y = readFloat(data, index)
			index += 4
		else:
			byte1 = readByte(data, index)
			byte2 = readByte(data, index+1)
			#printAsHex(data[index:index+8])
			#player_x = readInteger(data, index)
			index += 2
			#print str(byte1) + " " + str(byte2)
			player_x = byte1*16 + byte2/16 #player_x >> 8
			#player_x = int(player_x&0xf)*16+int(player_x&0xf0)/16
			
			#index = index + 2

			player_y = readInteger(data, index)
			index += 4
			player_y = int(player_y&0xf)*16+int(player_x&0xf0)/16

			#print(':'.join(x.encode('hex') for x in data[index:index+17]))

		#index = index + 24 - 16

		#print "index:" + str(index)

		if not players_have_teams and racetime < 10000:
			player = playerByIndex(i)
			if player:
				setTeam(player, player_x, player_y)

	players_have_teams = True
			#print player.name

		#print "x: " + str(player_x) + " y: " + str(player_y)
		#print "next"
	#print ""

	#print(':'.join(x.encode('hex') for x in data))
	
	#print (data[0:length])


def handleMessage(length, type, data):
	#print "length " + str(length)
	#print "type " + str(type)
	
	# File Header
	if (type == 500):
		handleFileHeader(length, data)

	# Game Header
	if (type == 5):
		handleHeader(length, data)

	# Chat
	if (type == 11):
		handleChat(length, data)

	# Race State Update
	if (type == 9):
		handleRaceState(length, data)

	pass

files = sys.argv[1:]

for file_name in files:

	# Skip directories
	if (os.path.isdir(file_name)):
		continue

	with gzip.open(file_name, "rb") as file:

		players = {}
		players_have_teams = False

	#with open(file_name, "rb") as file:
		rawfile = file.read()

		fileIndex = 0

		fileLength = len(rawfile)
		#print fileLength

		while fileIndex < fileLength:

			#print "fileIndex " + str(fileIndex)

			message_length = readInteger(rawfile, fileIndex)
			message_type = readInteger(rawfile, fileIndex + 4)

			short_message = (message_length & 0xff000000) != 0
			#print "short_message: " + str(short_message)

			if short_message or message_length == 0:
				message_length = 2

			#print "message_length: " + str(message_length)

			if not short_message:
				handleMessage(message_length, message_type, rawfile[fileIndex+8 : fileIndex+8+message_length])

			if (message_length > 0 and not short_message):
				fileIndex = fileIndex + message_length + 4
			else:
				fileIndex = fileIndex + 2



for player in all_players.values():
	player.dump_stats()
	print " "

