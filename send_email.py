import os
import smtplib
import sys
from email.message import EmailMessage

sender = "ourfrontlineded@icloud.com"
recipient = "nrn1298@gmail.com"
password = os.environ["ICLOUD_APP_PASSWORD"]

body = sys.stdin.read().strip()
if not body:
    body = "競輪チェックの結果がありません。"

msg = EmailMessage()
msg["From"] = sender
msg["To"] = recipient
msg["Subject"] = "競輪 自動チェック結果"
msg.set_content(body)

with smtplib.SMTP("smtp.mail.me.com", 587, timeout=30) as smtp:
    smtp.starttls()
    smtp.login(sender, password)
    smtp.send_message(msg)

print("Email sent successfully")
