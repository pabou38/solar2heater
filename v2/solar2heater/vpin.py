#!/usr/bin/python3

# vpin
v_automation = 0 # manual master switch
v_led_automation = 1
v_select = 2 # select primary heater
v_terminal = 5

# power. used in top graph, ie router, living room, kitchen
v_power_shelly = 3 
v_power_meross = 4
v_power_eddy = 6  

# power, used in botton graph
v_power_grid = 7
v_power_production = 8

# button manual on off
#v_shellyonoff = 9 
#v_merossonoff = 10

# red led, feedback on off
v_led_shelly = 11 
v_led_meross = 12

# temperature
v_temp_shelly = 13 
v_temp_meross = 14

v_log = 15 # push to display log in terminal
v_refresh = 17 # push refresh gauge (normally upodated only if automation update, or manual on:off, or every n cycle)
v_total_heater = 16 # eddy + all heaters 
v_monit = 18 # terminal, monit summary

v_sleep = 19 # sec beetween cycle
v_react_to_surplus = 20 # wait cycles before taking action
v_react_to_soutir = 21

v_last_actions = 22 # persistent, str, records last couple of action (on, off)

# what to do when automation is turned off (turn heaters off, or leave as it)
# True: turn heater off
# False: leave as it
v_automation_off_turn_heater_off = 23 

# Shelly HT reports value 
v_HT_temp = 24
v_HT_humid = 25
v_HT_stamp = 26


#####################
# colors, labels, content
# easier to manage here than in the code
# WARNING: only subset of what is in the GUI. some cannoyt be set with API, or are just not managed via API
#####################

# define some color to reuse (consistency)
# set by app: menu selection
# set in GUI creation: label of gracph, off state for heater manual control
color_heater = "#34c6eb"  # blue

web = " (Web)"
gui = " (GUI)"

auto_enabled = "enabled"
auto_disabled = "disabled"
auto_label ="automation status"
auto_color_enabled = "#00FF00"
auto_color_disabled = "#FF0000"

behavior_turn_off = "turn OFF"
behavior_leave = "leave AS IT"
behavior_label ="heater when automation disabled"
behavior_color_turn_off = "#FF0000"  # red, will turn off
behavior_color_leave = "#00FF00"