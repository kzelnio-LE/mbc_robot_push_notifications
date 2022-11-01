import smtplib
import requests
import os

from email.message import EmailMessage

g_user = os.environ['G_USER']
g_pass = os.environ.get('G_PASS')


def get_users(plant_config):
    url = plant_config["system"]["api_url"]
    r = requests.get(url=url)
    data = r.json()
    return data["users"]


def send_email(robot, alarm, timestamp, plant_config):
    msg = EmailMessage()
    to = ['5632002583@VTEXT.com']
    for user in get_users(plant_config):
        to.append(user["rows"]["phone"])
    msg['Subject'] = f"Robot {robot} Faulted - {timestamp}"
    msg['From'] = g_user
    msg['To'] = to
    body = f"{str(alarm)} - {timestamp}"
    msg.set_content(body)

    server_ssl = smtplib.SMTP_SSL('smtp.gmail.com', 465)
    server_ssl.ehlo()
    server_ssl.login(g_user, g_pass)
    server_ssl.send_message(msg, g_user, to)
    server_ssl.quit()
