#!/usr/bin/env python3

"""
Alin Georgescu
University Politehnica of Bucharest
Faculty of Automatic Control and Computers
Computer Engeneering Department

Math Bot (C) 2021 - Database adapter and initializer
"""

import json
import sys
import os
import requests

from argparse  import ArgumentParser
from time import sleep
from flask import Flask, Response, request

import jsonschema

# The Flask server's object
app = Flask(__name__)
# Debug activation flag
DEBUG = None

def validate_json(json_data, json_schema):
    """
    Check if a JSON object follow a schema or not.

    Args:
        json_data (dict): The input JSON obect.
        json_schema (dict): The wanted JSON schema.
    Returns:
        bool: True if the object is correct, False otherwise.
    """

    try:
        jsonschema.validate(instance=json_data, schema=json_schema)
    except jsonschema.exceptions.ValidationError:
        return False

    return True

@app.route("/api/register", methods=["POST"])
def register_msg():
    """
    Register a new user.

    Returns:
        Response: - 201 in case of success.
                  - 400 + "fields" if the body does not have all the necessary
                  information.
                  - 400 + "values" if the values are out of bounds.
                  - 409 if the user already exists.
    """

    body_schema = {
        "type": "object",
        "properties": {
            "user_id": {"type": "number"},
            "user_name": {"type": "string"}
        },
        "required": ["user_id", "user_name"]
    }

    payload = request.get_json(silent=True)

    is_valid = validate_json(payload, body_schema)
    if not is_valid:
        return Response(
            status=400,
            response="fields",
            mimetype="text/plain"
        )

    r = requests.post(DB_ADAPT_HOST + "/api/user", json=payload)

    return Response(
        status=r.status_code,
        response=r.text,
        mimetype="text/plain"
    )

@app.route("/api/courses", methods=["GET"])
def courses_msg():
    """
    Retrieve the available courses.

    Returns:
        Response: - 200 in case of success and the list of courses in the body.
    """

    r = requests.get(DB_ADAPT_HOST + "/api/courses")

    return Response(
        status=r.status_code,
        response=r.text,
        mimetype="application/json"
    )

@app.route("/api/enroll", methods=["POST"])
def enroll_msg():
    """
    Enroll an user to a course / change the course the user is pursuing.

    Returns:
        Response: - 200 in case of success.
                  - 400 if the body does not have all the necessary information.
                  - 404 + "no_course" if the course is not found.
                  - 404 + "no_user" if the user is not found.
                  - 500 if there was an internal error.
    """

    body_schema = {
        "type": "object",
        "properties": {
            "user_id": {"type": "number"},
            "course_name": {"type": "string"}
        },
        "required": ["user_id", "course_name"]
    }

    course_schema = {
        "type": "object",
        "properties": {
            "course_id": {"type": "number"},
            "course_name": {"type": "string"},
            "course_description": {"type": "string"},
            "course_num_steps": {"type": "number"},
            "course_num_questions": {"type": "number"}
        },
        "required": ["course_id", "course_name", "course_description",
                     "course_num_steps", "course_num_questions"]
    }

    payload = request.get_json(silent=True)

    is_valid = validate_json(payload, body_schema)
    if not is_valid:
        return Response(status=400)

    user_id = payload["user_id"]
    new_course_name = payload["course_name"]

    query_payload = {"course_name" : new_course_name}
    r = requests.get(f"{DB_ADAPT_HOST}/api/course", json=query_payload)

    if r.status_code == 404:
        return Response(
            status=404,
            response="no_course",
            mimetype="text/plain"
        )

    try:
        new_course = r.json()[0]
        is_valid = validate_json(new_course, course_schema)
        if not is_valid:
            return Response(status=500)

        new_course_id = new_course["course_id"]
    except (json.decoder.JSONDecodeError, TypeError):
        return Response(status=500)

    query_payload = {"user_id" : user_id, "fields" : ["course_id"]}
    r = requests.get(f"{DB_ADAPT_HOST}/api/user", json=query_payload)

    if r.status_code == 404:
        return Response(
            status=404,
            response="no_user",
            mimetype="text/plain"
        )

    try:
        user = r.json()[0]
        curr_course_id = user["course_id"]
    except (json.decoder.JSONDecodeError, TypeError):
        return Response(status=500)

    if new_course_id == curr_course_id:
        return Response(status=200)

    query_payload = {"user_id" : user_id, "user_step" : 1,
                     "course_id" : new_course_id, "user_test_started" : False}
    r = requests.put(DB_ADAPT_HOST + "/api/user", json=query_payload)

    if r.status_code != 200:
        return Response(status=500)

    return Response(
        status=r.status_code,
        response=json.dumps(new_course),
        mimetype="application/json"
    )

@app.route("/api/score/<int:user_id>", methods=["GET"])
def score_msg(user_id=None):
    """
    Retrieve a user's score.

    Returns:
        Response: - 200 in case of success.
                  - 404 if the user is not found.
                  - 500 if there was an internal error.
    """

    query_payload = {"user_id" : user_id, "fields": ["user_score"]}
    r = requests.get(DB_ADAPT_HOST + "/api/user", json=query_payload)

    if r.status_code == 404:
        return Response(status=404)
    elif r.status_code != 200:
        return Response(status=500)

    try:
        score = r.json()[0]["user_score"]
    except (json.decoder.JSONDecodeError, TypeError):
        return Response(status=500)

    return Response(
        status=200,
        response=str(score),
        mimetype="text/plain"
    )

@app.route("/api/cancel/<int:user_id>", methods=["POST"])
def cancel_msg(user_id=None):
    """
    Cancel a user's current activity.

    Returns:
        Response: - 200 in case of success and the canceled activity in body.
                  - 404 if the user is not found.
                  - 500 if there was an internal error.
    """

    query_payload = {"user_id" : user_id,
                     "fields" : ["course_id", "user_test_started"]}
    r = requests.get(DB_ADAPT_HOST + "/api/user", json=query_payload)

    try:
        user = r.json()[0]
        course_id = user["course_id"]
        user_test_started = user["user_test_started"]
    except (json.decoder.JSONDecodeError, TypeError):
        return Response(status=500)

    query_payload = {"user_id" : user_id, "user_step" : 0, "course_id" : None,
                     "user_test_started" : False}
    r = requests.put(DB_ADAPT_HOST + "/api/user", json=query_payload)

    if r.status_code == 404:
        return Response(status=404)
    elif r.status_code != 200:
        return Response(status=500)

    if user_test_started:
        reply = "test"
    elif course_id is not None:
        reply = "course"
    else:
        reply = ""

    return Response(
        status=200,
        response=reply,
        mimetype="text/plain"
    )

@app.route("/api/quit/<int:user_id>", methods=["POST"])
def quit_msg(user_id=None):
    """
    Add the user to a set waiting for confirmation when the command /quit is
    issued. After the confirmation the user will be deleted from the set and
    database.

    Returns:
        Response: - 200 in case of success.
                  - 205 if the user needs to confirm the action.
                  - 404 if the user is not found.
                  - 500 if there was an internal error.
    """

    query_payload = {"user_id" : user_id}
    r = requests.get(DB_ADAPT_HOST + "/api/user", json=query_payload)

    if r.status_code == 404:
        return Response(status=404)

    if r.status_code != 200:
        return Response(status=500)

    if user_id in WAIT_CONF_DEL:
        r = requests.delete(DB_ADAPT_HOST + "/api/user/" + str(user_id))
        if r.status_code != 200:
            return Response(status=500)

        WAIT_CONF_DEL.remove(user_id)

        return Response(status=200)

    WAIT_CONF_DEL.add(user_id)

    return Response(status=205)

@app.route("/api/message", methods=["POST"])
def recv_msg():
    """
    A route for receiving messages.

    Returns:
        Response: - 200 in case of success and the message to be sent back.
                  - 400 if the body is missing fields.
                  - 410 if the message was a user deletion confirmation and the
                  user was deleted.
                  - 500 if there was an internal error.
    """

    body_schema = {
        "type": "object",
        "properties": {
            "user_id": {"type": "number"},
            "message": {"type": "string"}
        },
        "required": ["user_id", "message"]
    }

    payload = request.get_json(silent=True)

    is_valid = validate_json(payload, body_schema)
    if not is_valid:
        return Response(status=400)

    user_id = payload["user_id"]
    msg = payload["message"]

    if user_id in WAIT_CONF_DEL:
        if msg[0].lower() == "y":
            r = requests.delete(DB_ADAPT_HOST + "/api/user/" + str(user_id))
            if r.status_code != 200:
                return Response(status=500)

            WAIT_CONF_DEL.remove(user_id)

            return Response(status=410)
        else:
            WAIT_CONF_DEL.remove(user_id)

            return Response(
                status=200,
                response="Quit aborted!",
                mimetype="text/plain"
            )


    # TODO

    return Response(
        status=200,
        response="",
        mimetype="application/json"
    )

@app.route("/", methods=["GET"])
def default():
    """
    A default route used for debugging.

    Returns:
        Response: - 200.
    """

    return Response(
        status=200,
        response=""" <html>
                     <body>
                     <h1>This is Math Bot's central application.</h1>
                     </body>
                     </html> """,
        mimetype="text/html"
    )

if __name__ == "__main__":
    parser = ArgumentParser(description="Run Math Bot's central application.")
    parser.add_argument("-d", "--debug", action="store_true",
                    help="specify if additional debug output should be shown")
    args = parser.parse_args()

    DEBUG = args.debug
    db_adapt_port = os.getenv("DB_ADAPT_PORT", "5000")
    DB_ADAPT_HOST = "http://database_adapter:" + db_adapt_port
    math_bot_port = int(os.getenv("MATH_BOT_PORT", "5001"))
    math_bot_addr = os.getenv("MATH_BOT_ADDR", "0.0.0.0")

    WAIT_CONF_DEL = set()

    app.run(host=math_bot_addr, port=math_bot_port, debug=DEBUG)
