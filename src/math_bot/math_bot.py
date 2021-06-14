#!/usr/bin/env python3
# pylint: disable=R0911,R0912

"""
Alin Georgescu
University Politehnica of Bucharest
Faculty of Automatic Control and Computers
Computer Engeneering Department

Math Bot (C) 2021 - Database adapter and initializer
"""

import logging
import json
import os
import sys

from argparse  import ArgumentParser
from time import localtime
from flask import Flask, Response, request

import jsonschema
import requests

from model import data_loader, predict

# The Flask server's object
app = Flask(__name__)

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

    req = requests.post(f"{DB_ADAPT_HOST}/api/user", json=payload)

    return Response(
        status=req.status_code,
        response=req.text,
        mimetype="text/plain"
    )

@app.route("/api/courses", methods=["GET"])
def courses_msg():
    """
    Retrieve the available courses.

    Returns:
        Response: - 200 in case of success and the list of courses in the body.
    """

    req = requests.get(f"{DB_ADAPT_HOST}/api/courses")

    return Response(
        status=req.status_code,
        response=req.text,
        mimetype="application/json"
    )

@app.route("/api/enroll", methods=["POST"])
def enroll_msg():
    """
    Enroll an user to a course / change the course the user is pursuing.

    Returns:
        Response: - 200 in case of success, if the new course is the same as the
                  old one.
                  - 200 + the information about the new course if success.
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

    # Get the course id, given the name.
    query_payload = {"course_name" : new_course_name}
    req = requests.get(f"{DB_ADAPT_HOST}/api/course", json=query_payload)

    if req.status_code == 404:
        return Response(
            status=404,
            response="no_course",
            mimetype="text/plain"
        )

    try:
        new_course = req.json()[0]
        is_valid = validate_json(new_course, course_schema)
        if not is_valid:
            return Response(status=500)

        new_course_id = new_course["course_id"]
    except (json.decoder.JSONDecodeError, TypeError):
        return Response(status=500)

    # Check if the user is enrolled and if the new course is actually the old
    # one.
    query_payload = {"user_id" : user_id, "fields" : ["course_id"]}
    req = requests.get(f"{DB_ADAPT_HOST}/api/user", json=query_payload)

    if req.status_code == 404:
        return Response(
            status=404,
            response="no_user",
            mimetype="text/plain"
        )

    try:
        user = req.json()[0]
        curr_course_id = user["course_id"]
    except (json.decoder.JSONDecodeError, TypeError):
        return Response(status=500)

    if new_course_id == curr_course_id:
        # The new course is actually the old one.
        return Response(status=200)

    # Change the user's course, but first clear "wait response" for the user.
    if user_id in WAIT_ANS:
        del WAIT_ANS[user_id]

    # Drop old user quit command.
    if user_id in WAIT_CONF_DEL:
        WAIT_CONF_DEL.remove(user_id)

    # Update user data.
    query_payload = {"user_id" : user_id, "user_step" : 1,
                     "course_id" : new_course_id, "user_test_started" : False}
    req = requests.put(f"{DB_ADAPT_HOST}/api/user", json=query_payload)

    if req.status_code != 200:
        return Response(status=500)

    return Response(
        status=req.status_code,
        response=json.dumps(new_course),
        mimetype="application/json"
    )

@app.route("/api/current_step/<int:user_id>", methods=["GET"])
def current_step(user_id=None):
    """
    Retrieve the current lesson / question for a user.

    Returns:
        Response: - 200 if success and the lesson's text (and picture) in body.
                  - 205 if success and the question's text in body.
                  - 403 if the user is not enrolled in an activity.
                  - 404 if the user is not found.
                  - 500 if there was an internal error.
    """

    query_payload = {"user_id" : user_id,
                     "fields": ["user_step", "course_id", "user_test_started"]}
    req = requests.get(f"{DB_ADAPT_HOST}/api/user", json=query_payload)

    if req.status_code == 404:
        return Response(status=404)

    if req.status_code != 200:
        return Response(status=500)

    try:
        user = req.json()[0]
        user_step = user["user_step"]
        course_id = user["course_id"]
        user_test_started = user["user_test_started"]
    except (json.decoder.JSONDecodeError, TypeError):
        return Response(status=500)

    if user_step == 0 or course_id is None:
        return Response(status=403)

    # If the current step is a test question, send it.
    if user_test_started:
        query_payload = {"test_step_inner_id" : user_step,
                         "course_id" : course_id}
        req = requests.get(f"{DB_ADAPT_HOST}/api/test_steps",
                           json=query_payload)
        if req.status_code != 200:
            return Response(status=500)

        try:
            test_step = req.json()[0]
            test_step_text = test_step["test_step_text"]
            test_step_id = test_step["test_step_id"]
        except (json.decoder.JSONDecodeError, TypeError):
            return Response(status=500)

        # Mark "wait test response" for the user.
        WAIT_ANS[user_id] = (test_step_id, course_id)

        return Response(
            status=205,
            response=f"test/{test_step_text}",
            mimetype="text/plain"
        )

    # If the current step is a mid question, send it, but first check that.
    req = requests.get(f"{DB_ADAPT_HOST}/api/course_steps/max/{course_id}")
    if req.status_code != 200:
        return Response(status=500)

    try:
        num_course_steps = req.json()[0]["max"]
    except (json.decoder.JSONDecodeError, TypeError):
        return Response(status=500)

    if user_step == (num_course_steps // 2 + 1):
        req = requests.get(f"{DB_ADAPT_HOST}/api/mid_questions/{course_id}")
        if req.status_code != 200:
            return Response(status=500)

        try:
            mid_question = req.json()[0]
            mid_question_text = mid_question["mid_question_text"]
        except (json.decoder.JSONDecodeError, TypeError):
            return Response(status=500)

        # Mark "wait mid question response" for the user.
        WAIT_ANS[user_id] = (0, course_id)

        return Response(
            status=205,
            response=f"mid/{mid_question_text}",
            mimetype="text/plain"
        )

    # If the current step is a lesson, send it.
    query_payload = {"course_step_inner_id" : user_step,
                     "course_id" : course_id}
    req = requests.get(f"{DB_ADAPT_HOST}/api/course_steps", json=query_payload)
    if req.status_code != 200:
        return Response(status=500)

    try:
        course_step = req.json()[0]
        course_step_text = course_step["course_step_text"]
        course_step_url = course_step["course_step_url"]
    except (json.decoder.JSONDecodeError, TypeError):
        return Response(status=500)

    payload = {"course_step_text" : course_step_text}
    if course_step_url is not None:
        payload["course_step_url"] = course_step_url

    return Response(
        status=200,
        response=json.dumps(payload),
        mimetype="application/json"
    )

@app.route("/api/next/<int:user_id>", methods=["POST"])
def next_msg(user_id=None):
    """
    Set the user to the next lesson / question.

    Returns:
        Response: - 200 if success.
                  - 403 if the user is not enrolled in an activity.
                  - 404 if the user is not found.
                  - 500 if there was an internal error.
    """

    # Clear "wait response" for the user.
    if user_id in WAIT_ANS:
        del WAIT_ANS[user_id]

    # Drop old user quit command.
    if user_id in WAIT_CONF_DEL:
        WAIT_CONF_DEL.remove(user_id)

    query_payload = {"user_id" : user_id,
                     "fields": ["user_step", "course_id", "user_test_started"]}
    req = requests.get(f"{DB_ADAPT_HOST}/api/user", json=query_payload)

    if req.status_code == 404:
        return Response(status=404)

    if req.status_code != 200:
        return Response(status=500)

    try:
        user = req.json()[0]
        user_step = user["user_step"]
        course_id = user["course_id"]
        user_test_started = user["user_test_started"]
    except (json.decoder.JSONDecodeError, TypeError):
        return Response(status=500)

    if user_step == 0 or course_id is None:
        return Response(status=403)

    if user_test_started:
        # Check if the user finished his test - if so, unenroll the user.
        req = requests.get(f"{DB_ADAPT_HOST}/api/test_steps/max/{course_id}")
        if req.status_code != 200:
            return Response(status=500)

        try:
            max_step = req.json()[0]["max"]
        except (json.decoder.JSONDecodeError, TypeError):
            return Response(status=500)

        if user_step >= max_step:
            query_payload = {"user_id" : user_id, "user_step" : 0,
                             "course_id" : None, "user_test_started" : False}
            req = requests.put(f"{DB_ADAPT_HOST}/api/user", json=query_payload)

            if req.status_code != 200:
                return Response(status=500)

            return Response(
                status=200,
                response="test_finished",
                mimetype="text/plain"
            )
    else:
        # Check if the user finished his course - if so,start the user's test.
        req = requests.get(f"{DB_ADAPT_HOST}/api/course_steps/max/{course_id}")
        if req.status_code != 200:
            return Response(status=500)

        try:
            max_step = req.json()[0]["max"]
        except (json.decoder.JSONDecodeError, TypeError):
            return Response(status=500)

        if user_step >= max_step:
            query_payload = {"user_id" : user_id, "user_step" : 1,
                            "user_test_started" : True}
            req = requests.put(f"{DB_ADAPT_HOST}/api/user", json=query_payload)

            if req.status_code != 200:
                return Response(status=500)

            return Response(
                status=200,
                response="test_started",
                mimetype="text/plain"
            )

    # Increase the user's step.
    query_payload = {"user_id" : user_id, "user_step" : user_step + 1}
    req = requests.put(f"{DB_ADAPT_HOST}/api/user", json=query_payload)

    if req.status_code != 200:
        return Response(status=500)

    return Response(status=200)

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
    req = requests.get(f"{DB_ADAPT_HOST}/api/user", json=query_payload)

    if req.status_code == 404:
        return Response(status=404)

    if req.status_code != 200:
        return Response(status=500)

    try:
        score = req.json()[0]["user_score"]
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

    # Clear "wait response" for the user.
    if user_id in WAIT_ANS:
        del WAIT_ANS[user_id]

    # Drop old user quit command.
    if user_id in WAIT_CONF_DEL:
        WAIT_CONF_DEL.remove(user_id)

    query_payload = {"user_id" : user_id,
                     "fields" : ["course_id", "user_test_started"]}
    req = requests.get(f"{DB_ADAPT_HOST}/api/user", json=query_payload)

    if req.status_code == 404:
        return Response(status=404)

    if req.status_code != 200:
        return Response(status=500)

    try:
        user = req.json()[0]
        course_id = user["course_id"]
        user_test_started = user["user_test_started"]
    except (json.decoder.JSONDecodeError, TypeError):
        return Response(status=500)

    query_payload = {"user_id" : user_id, "user_step" : 0, "course_id" : None,
                     "user_test_started" : False}
    req = requests.put(f"{DB_ADAPT_HOST}/api/user", json=query_payload)

    if req.status_code != 200:
        return Response(status=500)

    if user_test_started:
        reply = "test"
    elif course_id is not None:
        reply = "course"
    else:
        # The user was not enrolled.
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
    req = requests.get(f"{DB_ADAPT_HOST}/api/user", json=query_payload)

    if req.status_code == 404:
        return Response(status=404)

    if req.status_code != 200:
        return Response(status=500)

    if user_id in WAIT_CONF_DEL:
        req = requests.delete(f"{DB_ADAPT_HOST}/api/user/{user_id}")
        if req.status_code != 200:
            return Response(status=500)

        WAIT_CONF_DEL.remove(user_id)

        if user_id in WAIT_ANS:
            del WAIT_ANS[user_id]

        return Response(status=200)

    WAIT_CONF_DEL.add(user_id)

    return Response(status=205)

@app.route("/api/message", methods=["POST"])
def recv_msg():
    """
    A route for receiving messages.

    Returns:
        Response: - 200 + "hit" if the message received was the correct answer
                  to a question.
                  - 200 + "miss" if the message received was the wrong answer to
                  a question.
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

    # Check if the message is a confirmation for the user's quit command.
    if user_id in WAIT_CONF_DEL:
        if msg[0].lower() == "y":
            req = requests.delete(f"{DB_ADAPT_HOST}/api/user/{user_id}")
            if req.status_code != 200:
                return Response(status=500)

            WAIT_CONF_DEL.remove(user_id)

            if user_id in WAIT_ANS:
                del WAIT_ANS[user_id]

            return Response(status=410)

        WAIT_CONF_DEL.remove(user_id)

        return Response(
            status=200,
            response="Quit aborted!",
            mimetype="text/plain"
        )

    # Check if the message is an answer.
    if user_id in WAIT_ANS:
        (test_step_id, course_id) = WAIT_ANS[user_id]
        # Clear "wait response" for the user.
        del WAIT_ANS[user_id]

        if test_step_id == 0:
            req = requests.get(f"{DB_ADAPT_HOST}/api/mid_questions/{course_id}")
            if req.status_code != 200:
                return Response(status=500)

            try:
                test_step = req.json()[0]
                ref = test_step["mid_question_ans"]
            except (json.decoder.JSONDecodeError, TypeError):
                return Response(status=500)
        else:
            req = requests.get(f"{DB_ADAPT_HOST}/api/test_steps/{test_step_id}")
            if req.status_code != 200:
                return Response(status=500)

            try:
                test_step = req.json()[0]
                ref = test_step["test_step_ans"]
            except (json.decoder.JSONDecodeError, TypeError):
                return Response(status=500)

        # Compare the answer to the reference question.
        result = predict((msg, ref), COMPARE_THRESHOLD, MODEL, VOCAB)
        RESPONE_LOGGER.info("\"%s\",\"%s\",%d", msg, ref, result)

        if result:
            if test_step_id != 0:
                req = requests.put(f"{DB_ADAPT_HOST}/api/user/{user_id}/score")

                if req.status_code != 200:
                    return Response(status=500)

            return Response(
                status=200,
                response="hit",
                mimetype="text/plain"
            )

        return Response(
            status=200,
            response="miss",
            mimetype="text/plain"
        )

    return Response(status=200)

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

    # Debug activation flag
    DEBUG = args.debug
    logging.basicConfig(format="[%(levelname)s] %(asctime)s - %(message)s",
                        datefmt="%Y-%m-%d %H:%M:%S")
    logging.Formatter.converter = localtime
    logging.StreamHandler(sys.stdout)
    # The debugging logging module
    LOGGER = logging.getLogger(__name__)

    if DEBUG:
        LOGGER.setLevel(logging.DEBUG)
    else:
        LOGGER.setLevel(logging.WARNING)

    LOGGER.info("The central component started!")

    db_adapt_port = os.getenv("DB_ADAPT_PORT", "5000")
    DB_ADAPT_HOST = f"http://database_adapter:{db_adapt_port}"
    math_bot_port = int(os.getenv("MATH_BOT_PORT", "5001"))
    math_bot_addr = os.getenv("MATH_BOT_ADDR", "0.0.0.0")

    # Set with user who need to confirm quit command.
    WAIT_CONF_DEL = set()
    # Dictionary with users who need to response a question.
    # WAIT_ANS[user_id] = (test_step_id, course_id)
    # test_step_id will be 0 if the question is not from a test (is a mid
    # course question).
    WAIT_ANS = dict()

    COMPARE_THRESHOLD = 0.5
    (VOCAB, MODEL) = data_loader("model/data/en_vocab.txt",
                                 "model/trax_model/model.pkl.gz")

    # The user responses to be used for retraining the model.
    RESPONE_LOGGER = logging.getLogger("Response logger")
    handler = logging.FileHandler("/tmp/logs/user_input.csv", "w")
    RESPONE_LOGGER.addHandler(handler)
    RESPONE_LOGGER.setLevel(logging.INFO)
    RESPONE_LOGGER.info("message, reference, prediction")

    app.run(host=math_bot_addr, port=math_bot_port, debug=DEBUG)
