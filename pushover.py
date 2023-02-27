#!/usr/bin/python3

# i8suasztme@pomail.net

# app: domoticz , gabion, teleinfo, thingspeak, pi tinkering

# The httplib module has been renamed to http.client in Python 3.0.
# This module defines classes which implement the client side of the HTTP and H>
# the module urllib uses it to handle URLs that use HTTP and HTTPS.
import http.client as httplib  # httplib only P2
import urllib
import logging
import datetime
import time

import secret

# https://pushover.net/api#sounds
# https://support.pushover.net/i44-example-code-and-pushover-libraries

# token=azGDORePK8gMaC0QOYAMyEEuzJnyUi&user=uQiRzpo4DXghDmr9QzzfQu27cmVRsG
# &device=droid4
# &title=Backup+finished+-+SQL1
# &message=Backup+of+database+%22example%22+finished+in+16+minutes.


# python3
def send_pushover(message:str, title= "python", priority= 0, sound = "spacealarm"):
    message = "solar2heater: " + message

    conn = httplib.HTTPSConnection("api.pushover.net:443")

    conn.request("POST", "/1/messages.json",

    urllib.parse.urlencode({
        "token": secret.pushover["pushover_token"],
        "user": secret.pushover["pushover_user"],
        "message": message,
        "priority" : priority,
        "sound" : sound,
        "title" : title
        }), { "Content-type": "application/x-www-form-urlencoded" })
    conn.getresponse()

    try:
        logging.info(' send pushover:' + message )
    except:
        pass



if __name__ == "__main__":
    send_pushover('test', priority=1)
    time.sleep(2)
    #send_pushover('testing', priority=0, sound='cosmic')



"""
import requests
r = requests.post("https://api.pushover.net/1/messages.json", data = {
  "token": "APP_TOKEN",
  "user": "USER_KEY",
  "message": "hello world"
},
files = {
  "attachment": ("image.jpg", open("your_image.jpg", "rb"), "image/jpeg")
})
"""

"""
pushover - Pushover (default)   
bike - Bike   
bugle - Bugle   
cashregister - Cash Register   
classical - Classical   
cosmic - Cosmic   
falling - Falling   
gamelan - Gamelan   
incoming - Incoming   
intermission - Intermission   
magic - Magic   
mechanical - Mechanical   
pianobar - Piano Bar   
siren - Siren   
spacealarm - Space Alarm   
tugboat - Tug Boat   
alien - Alien Alarm (long)   
climb - Climb (long)   
persistent - Persistent (long)   
echo - Pushover Echo (long)   
updown - Up Down (long)   
vibrate - Vibrate Only
none - None (silent)
"""

"""
Lowest Priority (-2)
When the priority parameter is specified with a value of -2, messages will be considered lowest priority and will not generate any notification. On iOS, the application badge number will be increased.

Low Priority (-1)
Messages with a priority parameter of -1 will be considered low priority and will not generate any sound or vibration, but will still generate a popup/scrolling notification depending on the client operating system. Messages delivered during a user's quiet hours are sent as though they had a priority of (-1).

Normal Priority (0)
Messages sent without a priority parameter, or sent with the parameter set to 0, will have the default priority. These messages trigger sound, vibration, and display an alert according to the user's device settings. On iOS, the message will display at the top of the screen or as a modal dialog, as well as in the notification center. On Android, the message will scroll at the top of the screen and appear in the notification center.

If a user has quiet hours set and your message is received during those times, your message will be delivered as though it had a priority of -1.

High Priority (1)
Messages sent with a priority of 1 are high priority messages that bypass a user's quiet hours. These messages will always play a sound and vibrate (if the user's device is configured to) regardless of the delivery time. High-priority should only be used when necessary and appropriate.
"""
