#!/usr/bin/env python3

"""
Alin Georgescu
University Politehnica of Bucharest
Faculty of Automatic Control and Computers
Computer Engeneering Department

Math Bot (C) 2021 - The adapter to the Facebook Messenger frontend.
"""

import logging
import json
import os
import requests
import sys

from time import localtime, strftime
from argparse import ArgumentParser

import jsonschema
import telegram as tg
import telegram.ext as tge

# welcome to the course! + course_desc + Get ready to start

# Debug activation flag
DEBUG = None
LOGGER = None

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

def start_cmd(update: tg.Update, _: tge.CallbackContext) -> None:
    """
    Send a message when the command /start is issued.

    Args:
        update (telegram.Update): The incoming update.
        _ (telegram.ext.CallbackContext): Unused callback.
    """

    LOGGER.info(f"{update.message.text} received")

    user = update.effective_user

    payload = {"user_id" : user.id, "user_name" : user.full_name}
    r = requests.post(f"{MATH_BOT_HOST}/api/register", json=payload)
    LOGGER.info(f"Register POST {r.status_code}")

    if r.status_code == 409:
        update.message.reply_text("We already started. 🤔")
    elif r.status_code != 201:
        update.message.reply_text("Something happened.")
    else:
        update.message.reply_markdown_v2(
            f"Hi {user.mention_markdown_v2()}\!\n"
            "This is MathBot🤖, your new teacher\! I will help you learn Maths "
            "and ask you some questions after that\. Feel free to use my "
            "abilities\!\n"
            "Type /help for additional information\.\n"
            "Type /courses to list available lectures\.\n"
            "Type /enroll *course\_name* to get enrolled\.\n"
            "Have fun\!"
        )

def help_cmd(update: tg.Update, _: tge.CallbackContext) -> None:
    """
    Send a message when the command /help is issued.

    Args:
        update (telegram.Update): The incoming update.
        _ (telegram.ext.CallbackContext): Unused callback.
    """

    LOGGER.info(f"{update.message.text} received")

    update.message.reply_markdown_v2(
        "I am MathBot🤖, the new Maths teacher in town\!\n"
        "You can control me by sending these commands:\n"
        "/start \- start the conversation with me 😎\n"
        "/help \- ask me for my knowledge 😜\n"
        "/gdpr \- read my GDPR policy 🏴‍☠️\n"
        "/courses \- list the available courses 📚\n"
        "/enroll *course\_name* \- enroll to a course 🤓\n"
        "/next \- advance to the next step while enrolled in a course 💡\n"
        "/score \- ask me your score 🦾\n"
        "/cancel \- close the current course or test 😔\n"
        "/quit \- close the conversation and I'll forget everything 😥\n"
        "/time \- get the current time 🤷‍\n"
    )

def gdpr_cmd(update: tg.Update, _: tge.CallbackContext) -> None:
    """
    Send the GDPR notice when the command /gdpr is issued.

    Args:
        update (telegram.Update): The incoming update.
        _ (telegram.ext.CallbackContext): Unused callback.
    """

    LOGGER.info(f"{update.message.text} received")

    update.message.reply_markdown_v2(
        "Collected data:\n  \- username\n  \- user id\n  \- score\n"
        "I care about your privacy and no other data will be stored\. The "
        "collected data is used strictly for the app's functionality\.\n"
        "MathBot is part of a Bachelor Thesis project, so your data won't be "
        "sold to anyone\.\n"
        "By continuing to use the bot, you accept the terms above\.\n"
        "You can have all your data deleted by typing /quit and by stopping "
        "using this chatbot\."
    )

def time_cmd(update: tg.Update, _: tge.CallbackContext) -> None:
    """
    Send Bucharest's local time when the command /time is issued.

    Args:
        update (telegram.Update): The incoming update.
        _ (telegram.ext.CallbackContext): Unused callback.
    """

    LOGGER.info(f"{update.message.text} received")

    local_time = strftime("%d-%m-%Y %H:%M:%S", localtime())

    update.message.reply_text(f"The time in Bucharest is: {local_time}.")

def courses_cmd(update: tg.Update, _: tge.CallbackContext) -> None:
    """
    Retrieve the available courses when the command /courses is issued.

    Args:
        update (telegram.Update): The incoming update.
        _ (telegram.ext.CallbackContext): Unused callback.
    """

    LOGGER.info(f"{update.message.text} received")

    r = requests.get(f"{MATH_BOT_HOST}/api/courses")
    LOGGER.info(f"Courses GET {r.status_code}")

    if r.status_code != 200:
        update.message.reply_text("Something happened.")
        return

    reply = "The list of available courses is:"
    try:
        for course in r.json():
            is_valid = validate_json(course, COURSE_SCHEMA)
            if not is_valid:
                update.message.reply_text("Something happened.")
                return

            reply += f"\n\- *{course['course_name']}*:"
            reply += f"\n  Course length: {course['course_num_steps']}"
            reply += f"\n  Test length: {course['course_num_questions']}"
            reply += f"\n  Description: {course['course_description']}"
    except json.decoder.JSONDecodeError:
        update.message.reply_text("Something happened.")
        return

    update.message.reply_markdown_v2(reply.replace(".", "\."))

def enroll_cmd(update: tg.Update, ctx: tge.CallbackContext) -> None:
    """
    Enroll an user to a course when the command /enroll is issued.

    Args:
        update (telegram.Update): The incoming update.
        ctx (telegram.ext.CallbackContext): The context callback.
    """

    LOGGER.info(f"{update.message.text} received")

    args = ctx.args
    if len(args) < 1:
        update.message.reply_markdown_v2(
            "Wrong command\! ☠️ Please provide a course name\!\n"
            "e\.g\. /enroll *course\_name*"
        )
        return

    course_name = args[0]
    user_id = update.effective_user.id
    payload = {"user_id" : user_id, "course_name" : course_name}
    r = requests.post(f"{MATH_BOT_HOST}/api/enroll", json=payload)
    LOGGER.info("Enroll POST " + str(r.status_code))

    if r.status_code == 404:
        if r.text == "no_user":
            update.message.reply_text(
                "You are not registered! 😡 Please type /start to begin!"
            )
        else:
            update.message.reply_markdown_v2(
                "That course does not exist\! 😥 Please type /enroll "
                "*a\_valid\_course\_name* to begin\!"
            )
        return
    elif r.status_code != 200:
        update.message.reply_text("Something happened.")
        return

    if r.text is None or r.text == "":
        return

    try:
        course = r.json()
    except json.decoder.JSONDecodeError:
        update.message.reply_text("Something happened.")
        return

    is_valid = validate_json(course, COURSE_SCHEMA)
    if not is_valid:
        update.message.reply_text("Something happened.")
        return

    reply = (
        f"You started a course: *{course['course_name']}*.\n"
        f"{course['course_description']}\n"
        f"The course has {course['course_num_steps']} learning steps. When "
        "reaching the course's middle, you will have one question which is not "
        "mandatory and can be skipped, if you want.\n"
        "After the course you will have a test with "
        f"{course['course_num_questions']} questions. Each correct question"
        " will get you 1 point.\nGood luck\! 🤞"
    )

    update.message.reply_markdown_v2(reply.replace(".", "\."))

def score_cmd(update: tg.Update, _: tge.CallbackContext) -> None:
    """
    Retrieve the user's score when the command /score is issued.

    Args:
        update (telegram.Update): The incoming update.
        _ (telegram.ext.CallbackContext): Unused callback.
    """

    LOGGER.info(f"{update.message.text} received")

    user_id = update.effective_user.id
    r = requests.get(f"{MATH_BOT_HOST}/api/score/{user_id}")
    LOGGER.info(f"Score GET {r.status_code}")

    if r.status_code == 404:
        update.message.reply_text(
            "You are not registered! 😡 Please type /start to begin!"
        )
    elif r.status_code != 200:
        update.message.reply_text("Something happened.")
        return

    reply = f"Your score is: {r.text}\. "
    score = int(r.text)
    if score < 10:
        reply += "Keep learning rookie\! 🤙"
    elif score < 15:
        reply += "Push some more\! 🔝"
    else:
        reply += "You rock\! 🤩"

    update.message.reply_markdown_v2(reply)

# def cancel_cmd(update: tg.Update, _: tge.CallbackContext) -> None:
#     """
#     Cancel the user's current activity when the command /cancel is issued.

#     Args:
#         update (telegram.Update): The incoming update.
#         _ (telegram.ext.CallbackContext): Unused callback.
#     """

#     LOGGER.info(f"{update.message.text} received")

#     user_id = update.effective_user.id
#     r = requests.post(f"{MATH_BOT_HOST}/api/cancel/{user_id}")
#     LOGGER.info(f"Cancel POST {r.status_code}")

#     if r.status_code == 404:
#         update.message.reply_text(
#             "You are not registered! 😡 Please type /start to begin!"
#         )
#         return

#     testul tau a fost anulat
#     cursul tau a fost anulat
#     update.message.reply_markdown_v2(reply)

def echo(update: tg.Update, _: tge.CallbackContext) -> None:
    """Echo the user message."""
    update.message.reply_text(update.message.text)

if __name__ == "__main__":
    parser = ArgumentParser(description="Run an adapter to the Telegram API.")
    parser.add_argument("-d", "--debug", action="store_true",
                    help="specify if additional debug output should be shown")
    args = parser.parse_args()

    DEBUG = args.debug
    logging.basicConfig(format="[%(levelname)s] %(asctime)s - %(message)s",
                        datefmt="%Y-%m-%d %H:%M:%S")
    logging.Formatter.converter = localtime
    logging.StreamHandler(sys.stdout)
    LOGGER = logging.getLogger(__name__)

    if DEBUG:
        LOGGER.setLevel(logging.DEBUG)
    else:
        LOGGER.setLevel(logging.WARNING)

    LOGGER.info("Telegram frontend started!")

    math_bot_port = os.getenv("MATH_BOT_PORT", "5001")
    MATH_BOT_HOST = f"http://math_bot:{math_bot_port}"
    API_TOKEN = os.getenv("API_TOKEN")

    if API_TOKEN is None:
        print("No token provided!")
        while(True):
            continue

    COURSE_SCHEMA = {
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

     # Create the Updater and pass it your bot's token.
    updater = tge.Updater(API_TOKEN)

    # Get the dispatcher to register handlers
    dispatcher = updater.dispatcher

    # on different commands - answer in Telegram
    dispatcher.add_handler(tge.CommandHandler("start", start_cmd))
    dispatcher.add_handler(tge.CommandHandler("help", help_cmd))
    dispatcher.add_handler(tge.CommandHandler("gdpr", gdpr_cmd))
    dispatcher.add_handler(tge.CommandHandler("time", time_cmd))
    dispatcher.add_handler(tge.CommandHandler("courses", courses_cmd))
    dispatcher.add_handler(tge.CommandHandler("enroll", enroll_cmd))
    # dispatcher.add_handler(tge.CommandHandler("next", next_cmd))
    dispatcher.add_handler(tge.CommandHandler("score", score_cmd))
    # dispatcher.add_handler(tge.CommandHandler("cancel", cancel_cmd))
    # dispatcher.add_handler(tge.CommandHandler("quit", quit_cmd))

    # on non command i.e message - echo the message on Telegram
    dispatcher.add_handler(tge.MessageHandler(tge.Filters.text & ~tge.Filters.command, echo))

    # Start the Bot
    updater.start_polling()

    # Run the bot until you press Ctrl-C or the process receives SIGINT,
    # SIGTERM or SIGABRT. This should be used most of the time, since
    # start_polling() is non-blocking and will stop the bot gracefully.
    updater.idle()
