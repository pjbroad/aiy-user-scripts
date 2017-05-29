#! /usr/bin/env python

import sys
import os
import requests
import json

# Copyright 2017 Paul Broadhead.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

class kodi(object):

	def __init__(self, config_file, keyword, params):
		self.keyword = keyword
		self.error_message = None
		self.response_message = None
		self.params = params
		if os.path.isfile(config_file):
			try:
				self.config = json.load(open(config_file))
			except Exception, e:
				self.error_message = "Config read error: %s" %(str(e))
				self.config = {"debug":False}
		else:
			self.config = {"host":None, "port":8080, "debug":False}
			with open(config_file, 'w') as outfile:
				json.dump(self.config, outfile, indent = 4)

	def have_server(self):
		return self.config.get('host', None) and self.config.get('port', None)

	def get_response(self):
		if self.error_message:
			return self.error_message
		elif self.response_message:
			return self.response_message
		else:
			return "Umm, nothing to say"

	def call_api(self, method, params=None):
		data = { "jsonrpc":"2.0", "id":1 }
		data['method'] = method
		if params:
			data['params'] = params
		url = "http://%s:%d/jsonrpc?request="%(self.config["host"].lower(), self.config["port"]) + json.dumps(data)
		if self.config["debug"]:
			print("Request [%s]" %(url))
		try:
			r = requests.get(url, timeout=10)
		except requests.exceptions.ConnectionError:
			self.error_message = "Request failed to connect"
		except requests.exceptions.Timeout:
			self.error_message ="Request timed out"
		except Exception, e:
			self.error_message ="Unknown request failed: %s" %(str(e))
		else:
			if not r.status_code == 200:
				self.error_message = "Request error code %d" %(r.status_code)
			else:
				if self.config["debug"]:
					print("Received:")
					print(json.dumps(r.json(), separators=(',',':'), indent=4))
				return r.json()
		return {}

	def get_speed(self, playerid):
		params = {"playerid": playerid, "properties":["speed"]}
		return self.call_api("Player.getProperties", params).get('result',{}).get('speed',-1)

	def get_albums(self):
		return self.call_api("AudioLibrary.GetAlbums").get('result', {}).get('albums', [])

	def get_songs(self):
		return self.call_api("AudioLibrary.GetSongs").get('result', {}).get('songs', [])

	def get_active(self):
		return self.call_api("Player.GetActivePlayers").get('result', [])

	def play(self):
		if len(self.params) < 1:
			self.response_message = "Specify something to play"
			return
		search_text = ' '.join(self.params).strip().lower()
		self.stop()
		self.unmute()
		for album in self.get_albums():
			if album['label'].lower() == search_text:
				params = { "item": {"albumid": album['albumid']} }
				if self.call_api("Player.Open", params).get('result','').lower() == "ok":
					self.response_message = "OK, I'm playing %s." %(album['label'])
				else:
					self.error_message = "Error trying to play, %s." %(album['label'])
				return
		for song in self.get_songs():
			if song['label'].lower() == search_text:
				params = { "item": {"songid": song['songid']} }
				if self.call_api("Player.Open", params).get('result','').lower() == "ok":
					self.response_message = "OK, I'm playing %s." %(song['label'])
				else:
					self.error_message = "Error trying to play, %s." %(song['label'])
				return
		self.response_message = "Sorry, I can't find %s." %(search_text)

	def stop(self):
		active = self.get_active()
		if len(active):
			for player in active:
				params = {"playerid": player['playerid']}
				if self.call_api("Player.Stop", params).get('result','').lower() == "ok":
					self.response_message = "OK, stopping"
				else:
					self.error_message = "Error stopping play"
		else:
			self.response_message = "Nothing playing"

	def play_next(self):
		self._move("next", "down")

	def play_previous(self):
		self._move("previous", "up")

	def _move(self, name, direction):
		active = self.get_active()
		if len(active):
			for player in active:
				params = {"playerid": player['playerid'], 'direction':direction}
				if self.call_api("Player.Move", params).get('result','').lower() == "ok":
					self.response_message = "OK, play %s" %(name)
				else:
					self.error_message = "Error, play %s" %(name)
		else:
			self.response_message = "Nothing playing"

	def mute(self):
		self._mute_unmute("mute", True)

	def unmute(self):
		self._mute_unmute("unmute", False)

	def _mute_unmute(self, name, mute):
		params = {"mute": mute}
		muted = self.call_api("Application.SetMute", params).get('result', None)
		if muted == None:
			self.error_message = "Error, %s failed" %(name)
		else:
			self.response_message = "OK, %s" %(name)

	def pause(self):
		self._pause_restart("paused", False)

	def restart(self):
		self._pause_restart("restarted", True)

	def _pause_restart(self, name, restart):
		active = self.get_active()
		if len(active):
			for player in active:
				toggle = False
				speed = self.get_speed(player['playerid'])
				if ((not restart) and (speed > 0)) or ((restart) and (speed == 0)):
					params = {"playerid": player['playerid']}
					if self.call_api("Player.PlayPause", params).get('result',None) != None:
						if restart:
							self.unmute()
						self.response_message = "OK %s" %(name)
					else:
						self.error_message = "Error %s failed" %(name)
				else:
					self.response_message = "Play already %s" %(name)
		else:
			self.response_message = "Nothing playing"

	def give_help(self):
		self.response_message = "To play music say: %s play, followed by the album or song title. " %(self.keyword)
		self.response_message += "To control playback use %s stop, %s pause or %s restart. " %(self.keyword, self.keyword, self.keyword)
		self.response_message += "You can also use %s next or %s previous to change track when playing an album." %(self.keyword, self.keyword)

	def fallback(self):
		self.response_message = "Unknown command, try %s help" %(self.keyword)


def main(config_file, keyword, params):
	if len(params) < 1:
		return "Try %s help" %(keyword)
	k = kodi(config_file, keyword, params[1:])
	if not k.have_server():
		return "You need to edit %s to configure the kodi script." %(os.path.basename(config_file))
	{ 'help':k.give_help, 'play':k.play, 'stop':k.stop, 'pause':k.pause, 'restart':k.restart,
	  'mute':k.mute, 'unmute':k.unmute, 'previous':k.play_previous, 'next':k.play_next }.get(params[0].lower(), k.fallback)()
	return k.get_response()


if __name__ == "__main__":

	if len(sys.argv) < 2:
		info = {
			"description": "Control Kodi media centre.", 
			"keywords": [ "kodi", "cody" ],
			"before-listen": "mute",
			"after-listen": "unmute"
		}
		print(json.dumps(info, separators=(',',':'), indent=4))
	else:
		print("%s" %(main(os.path.join(os.path.dirname(sys.argv[0]), "kodi_config.json"), sys.argv[1], sys.argv[2:])))

