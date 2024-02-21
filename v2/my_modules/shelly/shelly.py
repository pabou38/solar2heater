#!/usr/bin/python3

#dos2unix if created on remote vscode
# shelly 1PM

import json
import requests
from time import sleep
import datetime


print("Shelly gen1 API")

# also defined as OUTPUT SWITCHED ON URL, but does not seem to work
#url = "https://maker.ifttt.com/trigger/shelly/with/key/zUKalX-EjHShyQOAMNVpw?value1=ON&value2=shelly&value3=1PM"
#res = requests.post(url)
#print('IFTTT', res.text)

def relay(host:str, b:bool):

    if b:
        print('turn relay on')
        url = host + "relay/0?turn=on"
    else:
        print('turn relay off')
        url = host + "relay/0?turn=off"

    res = requests.post(url)

    if res.status_code != 200:
        print('error shelly REST ', res.status_code)
        return(None)
    else:
        print ('is on: ', res.json()['ison'])
        return(res.json())



def status(host:str):

    url = host + "status"
    res = requests.post(url)

    if res.status_code != 200:
        print('error shelly REST ', res.status_code)
        pprint.pprint(res.json())
        return(None)
    else:
        # meter and relay info
        print ('power drawn Watt', res.json()['meters'] [0] ['power']) # Current real AC power being drawn, in Watts
        print ('meter self check ', res.json()['meters'] [0] ['is_valid'])
        print ('time stamp ', datetime.datetime.fromtimestamp(res.json()['meters'] [0] ['timestamp']))
        print ('total Wmn ', res.json()['meters'] [0] ['total']) #Total energy consumed by the attached electrical appliance in Watt-minute
        print ('last 3mn, in Wm ', res.json()['meters'] [0] ['counters']) #Energy counter value for the last 3 round minutes in Watt-minute
        print ('is on ', res.json()['relays'][0]['ison'])
        print ('overpower ', res.json()['relays'][0]['overpower'])
        print ('temp ', res.json()['temperature'], res.json()['temperature_status'])

        return(res.json())

        """
        get status
        power drawn Watt 30.63
        meter self check  True
        time stamp  2022-10-19 12:16:12
        total Wmn  15
        last 3mn, in Wm  [0.0, 0.0, 0.0]
        is on  True
        overpower  False
        temp  33.78 Normal
        """


def cloud_status(server:str, id:str, key:str):

    url = server + "device/status?id=%s&auth_key=%s" %(id,key)

    res = requests.post(url)

    if res.status_code != 200:
        print('error shelly REST ', res.status_code)
        pprint.pprint(res.json())
        return(None)
    else:

        return(res.json())
    
def cloud_relay(server:str, id:str, key:str, b:bool):

    if b:
        t = "on"
    else:
        t = "off"

    url = server + "device/relay/control?id=%s&auth_key=%s&channel=0&turn=%s" %(id, key, t)
    print(url)

    res = requests.post(url)

    if res.status_code != 200:
        print('error shelly REST ', res.status_code)
        pprint.pprint(res.json())
        return(None)
    else:
        return(res.json())


if __name__ == "__main__":


    import sys
    import pprint

    sys.path.append("../my_modules")

    import secret1

    # https://shelly-api-docs.shelly.cloud/gen1/#shelly1-shelly1pm
    solar_1 = "http://192.168.1.188/"
    solar_2 = "http://192.168.1.189/"
 
    # https://shelly-api-docs.shelly.cloud/cloud-control-api/communication 
    # The request is HTTPS POST to the Server your devices are hosted at.

    # device id
    solar_1_id = secret1.solar_1
    solar_2_id = secret1.solar_2

    auth_key = secret1.shelly_cloud_auth_key 
    server_uri = secret1.shelly_cloud_server_uri

    print("\ngetting status (local):", solar_1)
    j = status(solar_1)
    pprint.pprint(j)


    print("\ngetting status (cloud):", solar_1_id)
    j = cloud_status(server_uri, solar_1_id, auth_key)
    pprint.pprint(j)

    print("\nturning relay off (cloud):", solar_2_id)
    j = cloud_relay(server_uri, solar_2_id, auth_key, False)
    pprint.pprint(j)

"""
/status 
is extended with information about the current state of the output channel as well as data from the power meter and external sensors (if available).

  include meters
{
"wifi_sta":{"connected":true,"ssid":"Freebox-382B6B","ip":"192.168.1.93","rssi":-78},
"cloud":{"enabled":true,"connected":true},
"mqtt":{"connected":false},
"time":"09:06","unixtime":1662879994,
"serial":4,"has_update":false,
"mac":"E09806A9E103",
"cfg_changed_cnt":0,
"actions_stats":{"skipped":0},

// array 
"relays":[{"ison":true,"has_timer":false,"timer_started":0,"timer_duration":0,"timer_remaining":0,"overpower":false,"source":"http"}],

// Note: Energy counters (in the counters array and total) will reset to 0 after reboot.
"meters":[{"power":0.00,"overpower":0.00,"is_valid":true,"timestamp":1662887194,"counters":[0.000, 0.000, 0.000],"total":0}],

// power Current real AC power being drawn, in Watts
// overpower Value in Watts, on which an overpower condition is detected
// isvalid Whether power metering self-checks OK
// counters counter value for the last 3 round minutes in Watt-minute
// Total energy consumed by the attached electrical appliance in Watt-minute

"inputs":[{"input":0,"event":"","event_cnt":0}],

// internal device temperature in °C
"temperature":32.43,
"overtemperature":false,
//
"tmp":{"tC":32.43,"tF":90.37, "is_valid":true},
// Temperature status of the device, "Normal", "High" or "Very High"
"temperature_status":"Normal",
"ext_sensors":{},
"ext_temperature":{},
"ext_humidity":{},
"update":{"status":"unknown","has_update":false,"new_version":"","old_version":"20220809-124723/v1.12-g99f7e0b"},
"ram_total":51272,
"ram_free":39336,
"fs_size":233681,
"fs_free":149094,
"uptime":93}


/settings
{"device":{"type":"SHSW-PM","mac":"E09806A9E103","hostname":"shelly1pm-E09806A9E103","num_outputs":1,"num_meters":1},"wifi_ap":{"enabled":false,"ssid":"shelly1pm-E09806A9E103","key":""},"wifi_sta":{"enabled":true,"ssid":"Freebox-382B6B","ipv4_method":"dhcp","ip":null,"gw":null,"mask":null,"dns":null},"wifi_sta1":{"enabled":false,"ssid":null,"ipv4_method":"dhcp","ip":null,"gw":null,"mask":null,"dns":null},"ap_roaming":{"enabled":false,"threshold":-70},"mqtt": {"enable":false,"server":"192.168.33.3:1883","user":"","id":"shelly1pm-E09806A9E103","reconnect_timeout_max":60.000000,"reconnect_timeout_min":2.000000,"clean_session":true,"keep_alive":60,"max_qos":0,"retain":false,"update_period":30},"coiot": {"enabled":true,"update_period":15,"peer":""},"sntp":{"server":"time.google.com","enabled":true},"login":{"enabled":false,"unprotected":false,"username":"admin"},"pin_code":"","name":null,"fw":"20220809-124723/v1.12-g99f7e0b","factory_reset_from_switch":true,"discoverable":false,"build_info":{"build_id":"20220809-124723/v1.12-g99f7e0b","build_timestamp":"2022-08-09T12:47:23Z","build_version":"1.0"},"cloud":{"enabled":true,"connected":true},"timezone":"Europe/Paris","lat":48.871349,"lng":2.321150,"tzautodetect":true,"tz_utc_offset":7200,"tz_dst":false,"tz_dst_auto":true,"time":"09:07","unixtime":1662880060,"led_status_disable":false,"debug_enable":false,"allow_cross_origin":false,"ext_switch_enable":false,"ext_switch_reverse":false,"ext_switch":{"0":{"relay_num":-1}},"actions":{"active":false,"names":["btn_on_url","btn_off_url","longpush_url","shortpush_url","out_on_url","out_off_url","lp_on_url","lp_off_url","report_url","report_url","report_url","ext_temp_over_url","ext_temp_under_url","ext_temp_over_url","ext_temp_under_url","ext_temp_over_url","ext_temp_under_url","ext_hum_over_url","ext_hum_under_url"]},"hwinfo":{"hw_revision":"prod-191219", "batch_id":1},"max_power":1500,"supply_voltage":1,"power_correction":1.00,"mode" :"relay","longpush_time":800,"relays":[{"name":null,"appliance_type":"relay","ison":true,"has_timer":false,"default_state":"on","btn_type":"toggle","btn_reverse":0,"auto_on":0.00,"auto_off":0.00,"schedule":false,"schedule_rules":[],"max_power":1500}],"ext_sensors":{},"ext_temperature":{},"ext_humidity":{},"eco_mode_enabled":true}

/shelly
{"type":"SHSW-PM","mac":"E09806A9E103","auth":false,"fw":"20220809-124723/v1.12-g99f7e0b","discoverable":false,"longid":1,"num_outputs":1,"num_meters":1}


/relay/0
{"ison":true,"has_timer":false,"timer_started":0,"timer_duration":0,"timer_remaining":0,"overpower":false,"source":"http"}

POST
turn	string	Accepted values are on, off, toggle. This will turn ON/OFF the respective output channel when request is sent
timer	number	A one-shot flip-back timer in seconds
"""


