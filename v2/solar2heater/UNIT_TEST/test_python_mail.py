#!/usr/bin/env python


import smtplib, ssl
from email.message import EmailMessage

port = 465  # For SSL
smtp_server = "smtp.gmail.com"
sender_email = "meaudrepabou@gmail.com"  # Enter your address
receiver_email = "pboudalier@gmail.com"  # Enter receiver address

import secret

password = secret.email_passwd

msg = EmailMessage()
msg.set_content("https://leimao.github.io/blog/Python-Send-Gmail/")
msg['Subject'] = "application password"
msg['From'] = sender_email
msg['To'] = receiver_email

context = ssl.create_default_context()
with smtplib.SMTP_SSL(smtp_server, port, context=context) as server:
    server.login(sender_email, password)
    server.send_message(msg, from_addr=sender_email, to_addrs=receiver_email)
