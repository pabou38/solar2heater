#!/usr/bin/pyton3

##################################
# decorator modules
# handy "wrapper" around functions 
# to be defined BEFORE FUNCTION (to be decorated) DEFINITION
##################################

from time import time, sleep
import datetime

# only work for function, not ramdom piece of code
 
# function are 1st class citizen. can be use as argument, be returned
def dec_elapse(func_to_be_decorated):

    ########################
    # define what to do "around" the function
    #######################

    def wrapper(*args, **kwargs):

        # do something before and after function to be decorated
        start = time() # float value that represents the seconds since the epoch.

        x = func_to_be_decorated(*args, **kwargs)

        elapse = time() - start
        print("elapse in sec from decorator: %0.2f sec" % elapse)

        return(x) # make sure the returned value of the function to be decorated is available

    return(wrapper)


"""
start_time = datetime.datetime.now()
end_time = datetime.datetime.now()

time_diff = (end_time - start_time)
execution_time_sec = time_diff.total_seconds() 

from time import perf_counter


"""

 
if __name__ == "__main__":
    print ("testing decorator")

    # replace this with syntaxis sugar
    #function_to_be_decorated = dec_elapse(function_to_be_decorated)


    @dec_elapse
    def function_to_be_decorated(n:int):
        print("start function to be decorated")
        for i in range(n):
            sleep(1)

        return(i) # returned value of function to be decorated


    ret = function_to_be_decorated(2)
    print(ret)






