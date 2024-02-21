#!/usr/bin/python3

BLYNK_TEMPLATE_ID = ""
BLYNK_DEVICE_NAME = "solar"
BLYNK_AUTH_TOKEN  = ""


hub_serial = ""
hub_pwd = ""
director_url = "https://director.myenergi.net"

# envoy-s host IP
envoy_host = '192.168.1.182'
#envoy_host = 'paboupicloud.zapto.org:13883'
# /home is web gui
# /stream/meter   non stoppable streaming
# /production.json single shot

# envoy installer password. for streaming API. not needed for production.json
envoy_password = ''
envoy_user = 'installer'

pushover = {
"pushover_token" : "",
"pushover_user" : ""
}

# application password
# https://myaccount.google.com/u/1/apppasswords


email_passwd = ""

dest_email = "@gmail.com"
sender_email = "@gmail.com"
