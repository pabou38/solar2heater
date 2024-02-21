#!/usr/bin/python3

import time
import datetime
import subprocess

import re
import logging

from requests import get

import smtplib, ssl
from email.message import EmailMessage
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from yattag import Doc

monit_output = "/home/pi/ramdisk/monit_ouput"

# get public ip
#pip = get('https://api.ipify.org').text
#print ('public ip :', pip)


#######################
# monit summary
#######################

def monit_summary() -> str:

	print('running monit summary')

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

		# assumes everthing is fine now !!

	else:
		print('monit web server is running, port 2812 already open')


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

		# error processing done in caller
		#if s.find('NOK',0,len(s)) != -1 or s.find('limit', 0, len(s)) != -1 or s.find('failed',0,len(s)) != -1: # ie found
		return(s)

	except Exception as e:
		s= "exception monit summary %s" %str(e)
		print(s)
		logging.error(s)
		return("")



#######################
# mail
#######################

def send_mail(sender_email, password, dest_email, subject="default subject", content="default content", html=False):

	port = 465  # For SSL    587 for tls
	smtp_server = "smtp.gmail.com"

	s= "sending email: subject: %s. content: %s" %(subject,content)
	print(s)
	logging.info(s)


	msg = EmailMessage()
	
	msg['Subject'] = subject
	msg['From'] = sender_email
	msg['To'] = dest_email

	if html:
		msg.add_header('Content-Type','text/html')
		#msg.set_payload('Body of <b>message</b>')
		msg.set_payload(content)

	else:
		# text
		msg.set_content(content)



	# The smtplib module defines an SMTP client session object that can be used to send mail to any internet machine with an SMTP or ESMTP listener daemon
	# https://docs.python.org/3/library/smtplib.html

	# html
	# https://stackoverflow.com/questions/882712/send-html-emails-with-python

	try:

		context = ssl.create_default_context()
		with smtplib.SMTP_SSL(smtp_server, port, context=context) as server:
			server.login(sender_email, password)

			# This is a convenience method for calling sendmail() with the message represented by an email.message.Message object. The arguments have the same meaning as for sendmail(), except that msg is a Message object.
			server.send_message(msg, from_addr=sender_email, to_addrs=dest_email)

			server.quit()

	except Exception as e:
		s= "exception sending email. %s" %(str(e))
		print(s)
		logging.error(s)


####################
# is monit summary returning an error ?
####################

# name status type
# type: process, host, ..
# name: defined in config file
# status OK, not monitored , 
def parse_monit_summary(s):

	if s.find('NOK',0,len(s)) != -1 or s.find('limit', 0, len(s)) != -1 or s.find('failed',0,len(s)) != -1 : # ie found
		return(False)
	else:
		return(True)



	# exception sending email. (535, b'5.7.8 Username and Password not accepted. Learn more at\n5.7.8  https://support.google.com/mail/?p=BadCredentials u24-20020a7bc058000000b003f173987ec2sm4868379wmc.22 - gsmtp')


if __name__ == "__main__":

	print("testing mail")

	import secret1

	from yattag import Doc

	doc = Doc()
	tag = doc.tag
	text = doc.text
	line = doc.line


	# with tag('h1') creates a <h1> tag. 
	#It will be closed at the end of the with block. This way you don't have to worry about closing your tags.


	with tag('h2'): 
		doc.attr(style="color:#6000FF;")
		#The text method takes a string, escapes it so that it is safe to use in a html document (&, <, > are replaced with &amp;, &lt; and &gt;) 
		#and appends the escaped string to the document.
		text('python gmail')

	with tag('b'):
		doc.attr(style="color:#FF0060;")
		text('in bold')
	
	

	with tag('p'):
		doc.attr(style="color:red;")

		with tag('ul'): # unordered list
			line('li', 'battery') # The <li> HTML element is used to represent an item in a list. It must be contained in a parent element: an ordered list (<ol>), an unordered list (<ul>),
			line('li', 'solar')

	with tag('p'):

		with tag('ul'): # unordered list
			doc.attr(style="color:red;")
			line('li', 'multi') # The <li> HTML element is used to represent an item in a list. It must be contained in a parent element: an ordered list (<ol>), an unordered list (<ul>),
			line('li', 'shunt')

	s = doc.getvalue() # str


	print("testing email from python and application password")
	send_mail(secret1.sender_email, secret1.email_passwd, secret1.dest_email, subject = "test python", content = s , html=True)


	print("testing monit")

	s = monit_summary()
	print(s)

	if parse_monit_summary(s):
		print("monit summary is OK")
	else:
		print("monit reported an error")


