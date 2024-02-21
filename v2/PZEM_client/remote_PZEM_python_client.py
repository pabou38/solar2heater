#!/usr/bin/env python

# python client for remote_pzem
# module imported by python application
# also used for testing


# https://realpython.com/python-sockets/

import socket
import json
import time
import sys

version = 1.10

print("remote pzem python library %0.2f" %version)

def remote_pzem_connect(server_ip, server_port, timeout=30, log = None):

    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    s = "connecting to ESP32 at: %s. timeout %d" %(server_ip, timeout)
    print(s)
    if log is not None:
        log.info("PZEM " + s)

    # need to be set based on nb retries
    sock.settimeout(timeout) # The connect() operation is also subject to the timeout setting, and in general it is recommended to call settimeout() before calling connect() 

    try:
        sock.connect((server_ip, server_port))
        s = "connected to ESP32"
        print(s)
        if log is not None:
            log.info("PZEM " + s)

        return(sock)
    except Exception as e:
        s = "cannot connect to ESP32/PZEM %s" %str(e)
        print(s)
        if log is not None:
            log.error("PZEM " + s)

        return(None)


# data "power", "amps" , "volt"
def remote_pzem_get_value(sock, data:str, nb_retry=5, log = None):

    j = {"data":data, "nb_retry": nb_retry}

    payload = json.dumps(j)
    payload = bytes(payload, encoding="utf-8")

    #print("sending on socket", payload)
    # sending on socket b'{"data": "volt", "nb_retry": 2}'

    try:
        #  Unlike send(), this method continues to send data from bytes until either all data has been sent or an error occurs. None is returned on success. On error, an exception is raised, 
        # and there is no way to determine how much data, if any, was successfully sent.
        l = len(payload)
        ret = sock.sendall(payload) # Comparison to None should be 'expr is not None'
        #print(l,ret) # 31 None
        
    except Exception as e:
        s = "exception sending to socket %s" %str(e)
        print(s)
        if log is not None:
                log.error("PZEM "+ s)

        return(None)
    
    else:
        if ret is not None:
            s = "PZEM, sendall does not return None"
            print(s)
            if log is not None:
                log.error("PZEM " + s)
            return(None)


        try:
            buff = sock.recv(128) # make sure large enough for json response, otherwize fragmented
            #print ("received from socket", buff, type(buff), len(buff))
            # received from socket b'{"value": 240.2, "data": "volt"}' <class 'bytes'> 32

            if not buff:
                s = "socket closed  by remote"
                print(s)
                if log is not None:
                    log.error("PZEM "+ s)
                  
                return(None)

            else:
                try:
                    # decode response
                    s1 = buff.decode('utf-8') # bytes to str
                    payload = json.loads(s1) # str to dict
                    #print("payload received " , payload, type(payload), payload.keys()) # dict
                    # payload received  {'value': 240.2, 'data': 'volt'} <class 'dict'> dict_keys(['value', 'data'])  

                    assert data == payload["data"]

                    # "value" is the returned value read
                    return(payload["value"])

                except Exception as e:
                    s = "exception json decode", str(e)
                    print(s)
                    if log is not None:
                        log.error("PZEM "+ s)

                    print(buff)
                    try:
                        print(s1)
                    except:
                        pass

                    try:
                        print(payload)
                    except:
                        pass

                    return(None)

        except Exception as e:
            s = "exception recv on socket %s" %str(e) # timed out
            print(s)
            if log is not None:
                log.error("PZEM "+ s)

            return(None)


if __name__ == "__main__":

    print("remote pzem client python. run as main")

    # 176   ac battery
    # 177   eddi

    server_ip = "192.168.1.177"
    server_port = 5000

    sock = remote_pzem_connect(server_ip, server_port)
    if sock is None:
        print("cannot connect to remote PZEM")
        sys.exit(1)
    else:
        print("reading values\n")


    while True:

        try:

            for x in ["volt", "amps", "power"]:
                
                val = remote_pzem_get_value(sock, x, nb_retry=2)

                if val == None:
                    print("local error")

                if val == "None":
                    print("remote error")

                else:
                    print(x, val, type(val)) # power 119.6 <class 'float'>

            print('_________________')

            time.sleep(10)

        except Exception as e:
            print("exception: ",str(e))
            print("close socket")
            sock.close()
            sys.exit(0)








