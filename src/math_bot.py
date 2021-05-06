#!/usr/bin/env python3

"""
Alin Georgescu
University Politehnica of Bucharest
Faculty of Automatic Control and Computers
Computer Engeneering Department

Math Bot (C) 2021 - The agent's source code
"""

import os
import sys

from flask import Flask, Response, request
from pymessenger.bot import Bot

from model import data_loader, predict

app = Flask(__name__)

PORT = int(os.environ.get("PORT", "5000"))
ACCESS_TOKEN = os.environ.get("ACCESS_TOKEN")
VERIFY_TOKEN = os.environ.get("VERIFY_TOKEN")
bot = Bot(ACCESS_TOKEN)

(VOCAB, MODEL) = data_loader("model/data/en_vocab.txt",
                             "model/trax_model/model.pkl.gz")

@app.route("/", methods=["GET", "POST"])
def echo():
    """
    This is a simple echo function.
    """
    print("Func called")
    if request.method == "GET":
        print("Func is GET")
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
        print("Func is POST")
        output = request.get_json()

        for event in output["entry"]:
            messaging = event["messaging"]

            for msg in messaging:
                if msg.get("message"):

                    recipient_id = msg["sender"]["id"]

                    if msg["message"].get("text"):
                        message = msg["message"]["text"]
                        ref = "I like running in the park"
                        res = predict((message, ref), 0.7, MODEL, VOCAB)
                        bot.send_text_message(recipient_id, str(res))
                        print("MSG: " + message + "\n" + str(res))

    return Response(
        response="Success",
        status=200,
        mimetype="text/plain"
    )

if __name__ == "__main__":
    if ACCESS_TOKEN is None or VERIFY_TOKEN is None:
        sys.exit("Error! Token(s) not set!")

    app.run(host="0.0.0.0", port=PORT, debug=True)
