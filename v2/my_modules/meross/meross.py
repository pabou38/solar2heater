################ MEROSS ############################
meross_surplus = 'surplus' # name of plug MSS310
EMAIL = os.environ.get('MEROSS_EMAIL') or "pboudalier@gmail.com"
PASSWORD = os.environ.get('MEROSS_PASSWORD') or "domo38000" 

# V0.4.0.0 supports MSS210
#pip install meross-iot 
# Requirement already satisfied: meross-iot in c:\users\pboud\appdata\local\programs\python\python38\lib\site-packages (0.4.5.0)
# change python interpreter in vs code 3.8.5 

#print(sys.path)
# 'C:\\Users\\pboud\\AppData\\Local\\Programs\\Python\\Python38\\lib\\site-packages'

from meross_iot.http_api import MerossHttpClient
from meross_iot.manager import MerossManager

"""
a coroutine is a function that can suspend its execution before reaching return, and it can indirectly pass control to another coroutine for some time.
await asyncio.sleep(1)  the function yells up to the event loop and gives control back to it, 
saying, “I’m going to be sleeping for 1 second. Go ahead and let something else meaningful be done in the meantime.”

 time.sleep() can represent any time-consuming blocking function call, 
 while asyncio.sleep() is used to stand in for a non-blocking call (but one that also takes some time to complete)

the benefit of awaiting something, including asyncio.sleep(), is that the surrounding function 
can temporarily cede control to another function that’s more readily able to do something immediately.
In contrast, time.sleep() or any other blocking call is incompatible with asynchronous Python code, 
because it will stop everything in its tracks for the duration of the sleep time.
"""

# Windows and python 3.8 requires to set up a specific event_loop_policy. On Linux and MacOSX this is not necessary.
if os.name == 'nt':
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

#loop = asyncio.get_event_loop()
#loop.run_until_complete(main())
#loop.close()

# or asyncio.run(main())