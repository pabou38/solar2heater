#!/usr/bin/python3

from flask import Flask

from flask import request

import logging

def create_flask():

  print("creating flask")
  app = Flask(__name__)

  #02-15 01:09:01,766 192.168.1.50 - - [15/Feb/2024 01:09:01] "GET /temp/?hum=43&temp=22.25&id=shellyht-1BDD1B HTTP/1.1" 200 -

  log = logging.getLogger('werkzeug')
  log.setLevel(logging.ERROR)
  log.disabled = True

  #The canonical URL for the projects endpoint has a trailing slash. 
  #  It’s similar to a folder in a file system. If you access the URL without a trailing slash (/projects), Flask redirects you to the canonical URL with the trailing slash (/projects/).
  
  #The canonical URL for the about endpoint does not have a trailing slash. 
  # It’s similar to the pathname of a file. Accessing the URL with a trailing slash (/about/) produces a 404 “Not Found” error. 

  return(app)

def start_flask(app, port=5000):
  # https://flask.palletsprojects.com/en/3.0.x/api/#flask.Flask.run
  print("running flask")

  # debug = True seems to create problem when running as a thread
  app.run(host='0.0.0.0', port=port, debug=False)

  # If the debug flag is set the server will automatically reload for code changes 
  # and show a debugger in case an exception happened.

  # Set this to '0.0.0.0' to have the server available externally as well. Defaults to '127.0.0.1' 

  # does not return

# test with curl
# curl http://127.0.0.1:5500/temp/?hum=43
# flask log 127.0.0.1 - - [14/Feb/2024 14:31:32] "GET /temp/?hum=43 HTTP/1.1" 308 -

if __name__ == "__main__":

  automation = True

  app = create_flask()


  @app.route("/automation_off/", methods=['GET', 'POST'])
  def automation_off():
    return "<p>solar2heater automation OFF</p>"

  @app.route("/automation_on/", methods=['GET', 'POST'])
  def automation_on():
    print("inbound request:", request.method, request.path)
    return "<p>solar2heater automation ON</p>"
  
  @app.route("/automation/", methods=['GET', 'POST'])
  def automation_status():
    print("inbound request:", request.method, request.path)
    return "<p>automation %s</p>" %automation

  
  """
  route = /temp/   curl = /temp/?  ok, callback runs
  route = /temp/   curl = /temp?  receive dioc below, but callback does not run
        <title>Redirecting...</title>
        <h1>Redirecting...</h1>
        <p>You should be redirected automatically to the target URL: <a href="http://127.0.0.1:5500/temp/?hum=43">http://127.0.0.1:5500/temp/?hum=43</a>. If not, click the link.

  route = /temp   curl = /temp/?  ok, callback runs
  route = /temp   curl = /temp/?  404 not found
  
  """
  @app.route("/temp/", methods=['GET', 'POST']) # define as /temp/ in shelly app
  def root():
    print("method:", request.method)
    print("path:", request.path)
    print("parameters:", request.args)
   

    # inbound method: GET
    # inbound path: /temp/
    # parameters: ImmutableMultiDict([('hum', '44'), ('temp', '20.75'), ('id', 'shellyht-1BDD1B')])

    # flask log: 192.168.1.50 - - [14/Feb/2024 14:24:11] "GET /temp/?hum=42&temp=21.38&id=shellyht-1BDD1B HTTP/1.1" 308 -

    # no return, return(None): TypeError: The view function for 'root' did not return a valid response. The function either returned None or ended without a return statement.
    return("") 


  start_flask(app, port = 5500)

  print("main, waining for requests")
