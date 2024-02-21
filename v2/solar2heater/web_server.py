#!/usr/bin/python3

from flask import Flask

from flask import request

import 

def create_flask():

  print("creating flask")
  app = Flask(__name__)

  #The canonical URL for the projects endpoint has a trailing slash. It’s similar to a folder in a file system. If you access the URL without a trailing slash (/projects), Flask redirects you to the canonical URL with the trailing slash (/projects/).
  #The canonical URL for the about endpoint does not have a trailing slash. It’s similar to the pathname of a file. Accessing the URL with a trailing slash (/about/) produces a 404 “Not Found” error. 

  return(app)

def start_flask(app, port = 5000):
  # https://flask.palletsprojects.com/en/3.0.x/api/#flask.Flask.run
  print("running flask", app)

  # debug = True seems to create problem when running as a thread
  app.run(host='0.0.0.0', port=port, debug=False)

  # If the debug flag is set the server will automatically reload for code changes 
  # and show a debugger in case an exception happened.

  # Set this to '0.0.0.0' to have the server available externally as well. Defaults to '127.0.0.1' 



if __name__ == "__main__":

  automation = True

  app = create_flask()

  # can write to automation button

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

  # http://192.168.1.206:5000/temp/  in shelly app
  @app.route("/temp/", methods=['GET', 'POST'])
  def HT():
    print("inbound request:", request.method, request.path)
    try:
      t = request.args ["temp"]
      h = request.args ["hum"]

    except Exception as e:
      pass

    return ("")


  start_flask(app)
