#!/usr/bin/python3

import time
import datetime
import subprocess
from email.mime.text import MIMEText
import re
import logging

from requests import get

import smtplib, ssl
from email.message import EmailMessage

import secret

monit_output = "/home/pi/ramdisk/monit_ouput"

# get public ip
#pip = get('https://api.ipify.org').text
#print ('public ip :', pip)

def monit_summary() -> str:

	print('monit status')

	# test is monit web server running 
	# shell = True to use pipe
	# echo $?
	result = subprocess.run(['/bin/nc', '-z' , "127.0.0.1" , '2812'], stdout=subprocess.DEVNULL) # 0 if found
	# ret code is an objet
	print('nc ret code ',result.returncode) # 1 if not found, 0 is found

	if result.returncode != 0:
		# monit http server not running
		print('port 2812 not there. reloading monit')
		subprocess.run(['sudo', '/usr/bin/monit', 'reload'])
		time.sleep(3)

	else:
		print('port 2812 already open')


	# run monit summary
	# Cannot open the control file '/etc/monit/monitrc' -- Permission denied
	try:
		result = subprocess.run(['sudo', '/usr/bin/monit', 'summary'], stdout=subprocess.PIPE)
		s = result.stdout.decode('utf-8')

		with open(monit_output, 'wb') as fp:
			fp.write(s.encode('utf-8'))

		# replace multiple space to fit in blynk terminal 
		s = re.sub('\s+', '  ', s)

		# header of monit summary
		s = re.sub('Service Name', '\nService', s)
		s = re.sub('Type', 'Type\n', s)

		# add new line
		s = re.sub('System', 'System\n', s)
		s = re.sub('Process', 'Process\n', s)
		s = re.sub('Filesystem', 'Filesystem\n', s)
		s = re.sub('Host', 'Host\n', s)
		s = re.sub('Network', 'Network\n', s)

		#print(s)
		#logging.info(str(datetime.datetime.now())+ ' monit summary %s' %s)
		return(s)

	except Exception as e:
		s= "exception monit summary %s" %str(e)
		print(s)
		logging.error(s)

# send email if some string are found in output of monit summary
#if s.find('NOK',0,len(s)) != -1 or s.find('limit', 0, len(s)) != -1 or s.find('failed',0,len(s)) != -1: # ie found



def send_mail(subject="default subject", content="default content"):

	dest_email = secret.dest_email
	sender_email = secret.sender_email

	s= "sending email: subject: %s. content: %s" %(subject,content)
	print(s)
	logging.info(s)

	port = 465  # For SSL    587 for tls
	smtp_server = "smtp.gmail.com"
	password = secret.email_passwd

	msg = EmailMessage()
	msg.set_content(content)
	msg['Subject'] = subject
	msg['From'] = sender_email
	msg['To'] = dest_email

	try:

		context = ssl.create_default_context()
		with smtplib.SMTP_SSL(smtp_server, port, context=context) as server:
			server.login(sender_email, password)
			server.send_message(msg, from_addr=sender_email, to_addrs=dest_email)

	except Exception as e:
		s= "exception sending email. %s" %(str(e))
		print(s)
		logging.error(s)
