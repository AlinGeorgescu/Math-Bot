#!/usr/bin/env python3
# pylint: disable=W1401

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
import sys

from argparse import ArgumentParser
from time import localtime, strftime

import jsonschema
import requests
import telegram as tg
import telegram.ext as tge

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

    LOGGER.info("%s received", update.message.text)

    user = update.effective_user

    query_payload = {"user_id" : user.id, "user_name" : user.full_name}
    req = requests.post(f"{MATH_BOT_HOST}/api/register", json=query_payload)
    LOGGER.info("Register POST %s", req.status_code)

    if req.status_code == 409:
        update.message.reply_text("We already started. 🤔")
    elif req.status_code != 201:
        update.message.reply_text("Something happened.")
    else:
        update.message.reply_markdown_v2(
            f"Hi {user.mention_markdown_v2()}\!\n"
            "This is MathBot🤖, your new teacher\! I will help you learn Maths"
            " and ask you some questions after that\. Feel free to use my "
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

    LOGGER.info("%s received", update.message.text)

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

    LOGGER.info("%s received", update.message.text)

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

    LOGGER.info("%s received", update.message.text)

    local_time = strftime("%d-%m-%Y %H:%M:%S", localtime())

    update.message.reply_text(f"The time in Bucharest is: {local_time}.")

def courses_cmd(update: tg.Update, _: tge.CallbackContext) -> None:
    """
    Retrieve the available courses when the command /courses is issued.

    Args:
        update (telegram.Update): The incoming update.
        _ (telegram.ext.CallbackContext): Unused callback.
    """

    LOGGER.info("%s received", update.message.text)

    req = requests.get(f"{MATH_BOT_HOST}/api/courses")
    LOGGER.info("Courses GET %s", req.status_code)

    if req.status_code != 200:
        update.message.reply_text("Something happened.")
        return

    reply = "The list of available courses is:"
    try:
        for course in req.json():
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

    LOGGER.info("%s received", update.message.text)

    cmd_args = ctx.args
    if len(cmd_args) < 1:
        update.message.reply_markdown_v2(
            "Wrong command\! ☠️ Please provide a course name\!\n"
            "e\.g\. /enroll *course\_name*"
        )
        return

    course_name = cmd_args[0]
    user_id = update.effective_user.id
    query_payload = {"user_id" : user_id, "course_name" : course_name}
    req = requests.post(f"{MATH_BOT_HOST}/api/enroll", json=query_payload)
    LOGGER.info("Enroll POST %s", req.status_code)

    if req.status_code == 404:
        if req.text == "no_user":
            update.message.reply_text(
                "You are not registered! 😡 Please type /start to begin!"
            )
        else:
            update.message.reply_markdown_v2(
                "That course does not exist\! 😥 Please type /enroll "
                "*a\_valid\_course\_name* to begin\!"
            )

        return

    if req.status_code != 200:
        update.message.reply_text("Something happened.")
        return

    if req.text is None or req.text == "":
        return

    try:
        course = req.json()
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

    req = requests.get(f"{MATH_BOT_HOST}/api/current_step/{user_id}")
    LOGGER.info("Enroll GET %s", req.status_code)

    if req.status_code != 200 or req.text == "":
        update.message.reply_text("Something happened.")
    else:
        # The message is a course step.
        try:
            course_step = req.json()
        except json.decoder.JSONDecodeError:
            update.message.reply_text("Something happened.")
            return

        update.message.reply_text("Your first lesson is here:")
        course_step_text = course_step["course_step_text"]
        update.message.reply_text(course_step_text)

        if "course_step_url" in course_step:
            course_step_url = course_step["course_step_url"]
            update.message.reply_photo(course_step_url)

        update.message.reply_text("Type /next for the next lesson.")

def next_cmd(update: tg.Update, _: tge.CallbackContext) -> None:
    """
    Move the user to the next step in the activity he is enrolled to, course or
    test, when the command /next is issued.

    Args:
        update (telegram.Update): The incoming update.
        ctx (telegram.ext.CallbackContext): The context callback.
    """

    LOGGER.info("%s received", update.message.text)

    user = update.effective_user
    user_id = user.id

    req = requests.post(f"{MATH_BOT_HOST}/api/next/{user_id}")
    LOGGER.info("Next POST %s", req.status_code)

    if req.status_code == 403:
        update.message.reply_text("You are not enrolled in any course!")
        return

    if req.status_code == 404:
        update.message.reply_text(
            "You are not registered! 😡 Please type /start to begin!"
        )
        return

    if req.status_code != 200:
        update.message.reply_text("Something happened.")
        return

    if req.text == "test_finished":
        update.message.reply_markdown_v2(
            f"Congratulations {user.mention_markdown_v2()}\!\n"
            "You finished your test\! 👏 Type /score to check your points\.\n"
            "Don't forget to /enroll to a new course\!"
        )
        return

    if req.text == "test_started":
        update.message.reply_markdown_v2(
            "You finished the course so fast\! 🤯\n"
            "Your test will start now\. Answer all your questions to maximize "
            "your score\."
        )

    req = requests.get(f"{MATH_BOT_HOST}/api/current_step/{user_id}")
    LOGGER.info("Next GET %s", req.status_code)

    if req.status_code == 200:
        # The message is a course step.
        try:
            course_step = req.json()
        except json.decoder.JSONDecodeError:
            return

        course_step_text = course_step["course_step_text"]
        update.message.reply_text(course_step_text)

        if "course_step_url" in course_step:
            course_step_url = course_step["course_step_url"]
            update.message.reply_photo(course_step_url)

        update.message.reply_text("Type /next for the next lesson.")
        return

    if req.status_code == 205 and req.text != "":
        # The message is a mid question or a test step.
        slash_pos = req.text.find("/")

        if slash_pos == -1:
            update.message.reply_text("Something happened.")
            return

        category = req.text[:slash_pos]
        question = req.text[slash_pos + 1:]

        if category == "test":
            update.message.reply_text(
                "Answer this question for 1 point or type /next to skip."
            )
            update.message.reply_text(question)
        else:
            update.message.reply_text(
                "Answer this question or type /next to skip."
            )
            update.message.reply_text(question)
    else:
        update.message.reply_text("Something happened.")

def score_cmd(update: tg.Update, _: tge.CallbackContext) -> None:
    """
    Retrieve the user's score when the command /score is issued.

    Args:
        update (telegram.Update): The incoming update.
        _ (telegram.ext.CallbackContext): Unused callback.
    """

    LOGGER.info("%s received", update.message.text)

    user_id = update.effective_user.id
    req = requests.get(f"{MATH_BOT_HOST}/api/score/{user_id}")
    LOGGER.info("Score GET %s", req.status_code)

    if req.status_code == 404:
        update.message.reply_text(
            "You are not registered! 😡 Please type /start to begin!"
        )
    elif req.status_code != 200:
        update.message.reply_text("Something happened.")
        return

    reply = f"Your score is: {req.text}\. "
    score = int(req.text)
    if score < 10:
        reply += "Keep learning rookie\! 🤙"
    elif score < 15:
        reply += "Push some more\! 🔝"
    else:
        reply += "You rock\! 🤩"

    update.message.reply_markdown_v2(reply)

def cancel_cmd(update: tg.Update, _: tge.CallbackContext) -> None:
    """
    Cancel the user's current activity when the command /cancel is issued.

    Args:
        update (telegram.Update): The incoming update.
        _ (telegram.ext.CallbackContext): Unused callback.
    """

    LOGGER.info("%s received", update.message.text)

    user_id = update.effective_user.id
    req = requests.post(f"{MATH_BOT_HOST}/api/cancel/{user_id}")
    LOGGER.info("Cancel POST %s", req.status_code)

    if req.status_code == 404:
        update.message.reply_text(
            "You are not registered! 😡 Please type /start to begin!"
        )
        return

    if req.status_code != 200:
        update.message.reply_text("Something happened.")
        return

    if req.text == "test":
        update.message.reply_text(
            "Your test has been cancelled! Your score was not affected."
        )
    elif req.text == "course":
        update.message.reply_text(
            "Your course has been cancelled!"
        )

def quit_cmd(update: tg.Update, _: tge.CallbackContext) -> None:
    """
    Add the user to a set waiting for confirmation when the command /quit is
    issued. After the confirmation the user will be deleted from the set and
    database.

    Args:
        update (telegram.Update): The incoming update.
        _ (telegram.ext.CallbackContext): Unused callback.
    """

    LOGGER.info("%s received", update.message.text)

    user_id = update.effective_user.id
    req = requests.post(f"{MATH_BOT_HOST}/api/quit/{user_id}")
    LOGGER.info("Quit POST %s", req.status_code)

    if req.status_code == 200:
        update.message.reply_text(
            "I am sad that you are leaving! 😥 See you around! 👋"
        )
    elif req.status_code == 205:
        update.message.reply_text(
            "Are you sure you want to quit? 🤔 All your progress will be lost! "
            "Type Yes/Y or /quit again for confirmation."
        )
    elif req.status_code == 404:
        update.message.reply_text(
            "You are not registered! 😡 Please type /start to begin!"
        )
    else:
        update.message.reply_text("Something happened.")

def unknown(update: tg.Update, _: tge.CallbackContext) -> None:
    """
    The handler to be called when an unknown command is issued.

    Args:
        update (telegram.Update): The incoming update.
        _ (telegram.ext.CallbackContext): Unused callback.
    """

    LOGGER.info("Unknown received %s", update.message.text)

    update.message.reply_text("Say what? I don't know that command. 😥")

def text_msg(update: tg.Update, _: tge.CallbackContext) -> None:
    """
    The text message handler. This checks if the message is a command
    confirmation, question answer or other message.

    Args:
        update (telegram.Update): The incoming update.
        _ (telegram.ext.CallbackContext): Unused callback.
    """

    LOGGER.info("Message received: %s", update.message.text)

    user_id = update.effective_user.id
    msg = update.message.text

    query_payload = {"user_id" : user_id, "message" : msg}
    req = requests.post(f"{MATH_BOT_HOST}/api/message", json=query_payload)
    LOGGER.info("Message POST %s", req.status_code)

    if req.status_code == 200:
        if req.text == "hit":
            update.message.reply_text(
                "That's right! 👍 Now type /next to continue."
            )
        elif req.text == "miss":
            update.message.reply_text(
                "Your answer is not the one. 👎 You'll have your chance!\n"
                "Now type /next to continue."
            )
        else:
            update.message.reply_text("Do what you need to do.")
    elif req.status_code == 410:
        update.message.reply_text(
            "I am sad that you are leaving! 😥 See you around! 👋"
        )
    else:
        update.message.reply_text("Something happened.")

if __name__ == "__main__":
    parser = ArgumentParser(description="Run an adapter to the Telegram API.")
    parser.add_argument("-d", "--debug", action="store_true",
                    help="specify if additional debug output should be shown")
    args = parser.parse_args()

    # Debug activation flag
    DEBUG = args.debug
    logging.basicConfig(format="[%(levelname)s] %(asctime)s - %(message)s",
                        datefmt="%Y-%m-%d %H:%M:%S")
    logging.Formatter.converter = localtime
    logging.StreamHandler(sys.stdout)
    # The logging module
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
        while True:
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

    # The Telegram updater.
    updater = tge.Updater(API_TOKEN)
    # Dispatcher for registering handlers.
    dispatcher = updater.dispatcher

    # Telegram command handlers.
    dispatcher.add_handler(tge.CommandHandler("start", start_cmd))
    dispatcher.add_handler(tge.CommandHandler("help", help_cmd))
    dispatcher.add_handler(tge.CommandHandler("gdpr", gdpr_cmd))
    dispatcher.add_handler(tge.CommandHandler("time", time_cmd))
    dispatcher.add_handler(tge.CommandHandler("courses", courses_cmd))
    dispatcher.add_handler(tge.CommandHandler("enroll", enroll_cmd))
    dispatcher.add_handler(tge.CommandHandler("next", next_cmd))
    dispatcher.add_handler(tge.CommandHandler("score", score_cmd))
    dispatcher.add_handler(tge.CommandHandler("cancel", cancel_cmd))
    dispatcher.add_handler(tge.CommandHandler("quit", quit_cmd))
    # Telegram handler for unknown commands.
    dispatcher.add_handler(tge.MessageHandler(tge.Filters.command, unknown))
    # Telegram handler for text messages.
    dispatcher.add_handler(tge.MessageHandler(tge.Filters.text, text_msg))

    # Start the Bot
    updater.start_polling()

    # Run the bot until Ctrl-C is pressed or the process receives SIGINT,
    # SIGTERM or SIGABRT.
    updater.idle()
