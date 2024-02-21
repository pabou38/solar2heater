 # shared variable between Blynk and the rest


# read by blynk.run thread in my_blynk_private. set by disconnect() in deep_sleep.py
# both are imported (move disconnect in deep_sleep module to make it generic and less code in main
stop_run = False
 