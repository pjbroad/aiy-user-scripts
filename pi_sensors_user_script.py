#! /usr/bin/env python

"""AIY voice project user script - Speak readings from pi_sensors.
Just another example but perhaps useful if your are running pi_sensors.
See https://github.com/pjbroad/pi_sensors
"""


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

import sys
import requests
import json
import os


def get_config():
    filename, file_extension = os.path.splitext(sys.argv[0])
    config_file = filename + ".json"
    if os.path.isfile(config_file):
        return json.load(open(config_file))
    else:
        config = {"url": "", "certfile": "", "rooms": [], "sensors": [], "mappings": {}}
        with open(config_file, 'w') as outfile:
            json.dump(config, outfile, indent=4)
    return None


def call_api(url, certfile):
    message = ""
    try:
        r = requests.get(url, verify=certfile, timeout=10)
    except requests.exceptions.ConnectionError:
        message = "Failed to connect to the server."
    except requests.exceptions.Timeout:
        message = "Timed out connecting to the server."
    except:
        message = "Unknown error connecting to the server."
    else:
        if r.status_code != 200:
            message = "Error code %d connecting to the server." % (r.status_code)
        else:
            return (message, r.json())
    return (message, {})


class pi_sensors(object):

    def __init__(self, args):
        self.room = None
        self.sensor = None
        config = get_config()
        if config is not None and len(config.get("url", "")) and \
                config.get("rooms", []) and config.get("sensors", []):
            self.config = config
        else:
            self.config = None
            return
        for arg in args:
            arg = arg.lower()
            if arg in self.config.get("mappings", []):
                arg = self.config["mappings"][arg]
            if arg in self.config.get("rooms", []):
                self.room = arg
            elif arg in self.config.get("sensors", []):
                self.sensor = arg
            elif arg == "help":
                self.room = "help"

    def _get_help(self):
        print(
            "Specify room and the type of reading, " +
            "e.g. sensors, what's the temperature in the study ?")

    def _get_reading(self):
        cert_file = self.config.get("certfile", None)
        if cert_file:
            cert_file = os.path.join(os.path.dirname(sys.argv[0]), cert_file)
        url = "%s/%s/%s/latest" % (self.config.get("url", ""), self.room, self.sensor)
        message, response = call_api(url, cert_file)
        readings = response.get("data", [])
        if len(readings) > 0:
            record = readings[0].get("record", {}).get("record", {})
            print(
                "The %s %s is %.1f %s"
                % (self.room, self.sensor, record.get("value", 0), record.get("units", "")))
        else:
            print("Sorry, I couldn't get a reading for that sensor. %s" % (message))

    def run(self):
        if self.config is None:
            print("Sorry, missing configuration")
        elif self.room == 'help':
            self._get_help()
        elif self.room in self.config.get("rooms", []):
            if self.sensor in self.config.get("sensors", []):
                self._get_reading()
            else:
                print("Sorry I couldn't identify the type of sensor.")
        else:
            print("Sorry I couldn't identify the room")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        info = {
            "description": "Get pi_sensors readings.",
            "keywords": ["sensor", "sensors", "census"],
        }
        print(json.dumps(info, separators=(',', ':'), indent=4))
    elif len(sys.argv) > 2:
        pi_sensors(sys.argv[2:]).run()
    else:
        print("Sorry, try sensors help")
