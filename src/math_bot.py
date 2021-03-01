#!/usr/bin/env python3

"""
Alin Georgescu
University Politehnica of Bucharest
Faculty of Automatic Control and Computers
Computer Engeneering Department

Math Bot (C) 2021
"""

import os

from flask import Flask, Response, request
from pymessenger.bot import Bot

app = Flask(__name__)

ACCESS_TOKEN = os.environ['ACCESS_TOKEN']
VERIFY_TOKEN = os.environ['VERIFY_TOKEN']
bot = Bot(ACCESS_TOKEN)

@app.route("/", methods=["GET", "POST"])
def hello():
    if request.method == "GET":
        if request.args.get("hub.verify_token") == VERIFY_TOKEN:
            return Response(
                response=request.args.get("hub.challenge"),
                status=200,
                mimetype="text/plain"
            )

        return Response(
            response="Invalid verification token",
            status=401,
            mimetype="text/plain"
        )

    if request.method == "POST":
        output = request.get_json()

        for event in output["entry"]:
            messaging = event["messaging"]

            for x in messaging:
                if x.get("message"):

                    recipient_id = x["sender"]["id"]

                    if x["message"].get("text"):
                        message = x["message"]["text"]
                        bot.send_text_message(recipient_id, message)

                    if x["message"].get("attachments"):
                        for att in x["message"].get("attachments"):
                            bot.send_attachment_url(recipient_id, att["type"], att["payload"]["url"])

    return Response(
            response="Success",
            status=200,
            mimetype="text/plain"
        )

if __name__ == "__main__":
    app.run(port=5002, debug=True)
