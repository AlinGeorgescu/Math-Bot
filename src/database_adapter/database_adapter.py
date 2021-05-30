#!/usr/bin/env python3

"""
Alin Georgescu
University Politehnica of Bucharest
Faculty of Automatic Control and Computers
Computer Engeneering Department

Math Bot (C) 2021 - Database adapter and initializer
"""

import json
import os

from argparse  import ArgumentParser
from time import sleep
from flask import Flask, Response, request
from psycopg2.extras import RealDictCursor
from psycopg2 import sql

import jsonschema
import psycopg2
import psycopg2.errors

# The Flask server's object
app = Flask(__name__)
# Database connection controller object
CONN = None
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

def init_postgres_con():
    """
    Start the connection to the PostgreSQL database.
    """

    host = "database"
    database = os.getenv("POSTGRES_DB", "postgres")
    user = os.getenv("POSTGRES_USER", "admin")
    password = os.getenv("POSTGRES_PASSWORD", "adminpass")

    # Run in a loop until the database server starts.
    while True:
        try:
            pg_conn = psycopg2.connect(host=host, database=database,
                                       user=user, password=password)

            if DEBUG:
                print("Connection with database ready!")

            return pg_conn
        except psycopg2.OperationalError:
            sleep(1)

def populate_postgres():
    """
    Check if the table schema is correct. If the tables don't exist, they are
    created and populated.
    """

    data_file = os.environ.get("DATA_FILE", "courses.json")

    with open(data_file, "r") as fin:
        courses_data = json.load(fin)

    if DEBUG:
        print("Data file:", data_file, "\n")

    cursor = CONN.cursor()

    # Check the existence of "courses" table (and create it).
    cursor.execute(
        """
        SELECT EXISTS(
            SELECT * FROM information_schema.tables
            WHERE table_name=\'courses\'
        );
        """)

    if not cursor.fetchone()[0]:
        if DEBUG:
            print("Creating table courses")

        cursor.execute(
            """
            CREATE TABLE courses (
                course_id SERIAL2 PRIMARY KEY,
                course_name VARCHAR(10) NOT NULL,
                course_description VARCHAR(255) NOT NULL,
                course_num_steps INT2 NOT NULL,
                course_num_questions INT2 NOT NULL
            );
            """)

        for course in courses_data["courses"]:
            columns = list(course.keys())
            values = list(course.values())
            query = sql.SQL("INSERT INTO courses({}) VALUES({}) \
                             RETURNING course_id;").format(
                        sql.SQL(", ").join(map(sql.Identifier, columns)),
                        sql.SQL(", ").join(map(sql.Literal, values)),
                    )

            cursor.execute(query)

    # Check the existence of "course_steps" table (and create it).
    cursor.execute(
        """
        SELECT EXISTS(
            SELECT * FROM information_schema.tables
            WHERE table_name=\'course_steps\'
        );
        """)

    if not cursor.fetchone()[0]:
        if DEBUG:
            print("Creating table course_steps")

        cursor.execute(
            """
            CREATE TABLE course_steps (
                course_step_id SERIAL2 PRIMARY KEY,
                course_step_inner_id INT2 NOT NULL,
                course_step_text VARCHAR(500) NOT NULL,
                course_id INT2 NOT NULL,
                CONSTRAINT fk_course_id
                    FOREIGN KEY(course_id)
                    REFERENCES courses(course_id)
                    ON DELETE CASCADE
                    ON UPDATE CASCADE
            );
            """)

        for course_step in courses_data["course_steps"]:
            columns = list(course_step.keys())
            values = list(course_step.values())
            query = sql.SQL("INSERT INTO course_steps({}) VALUES({}) \
                             RETURNING course_step_id;").format(
                        sql.SQL(", ").join(map(sql.Identifier, columns)),
                        sql.SQL(", ").join(map(sql.Literal, values)),
                    )

            cursor.execute(query)

    # Check the existence of "mid_questions" table (and create it).
    cursor.execute(
        """
        SELECT EXISTS(
            SELECT * FROM information_schema.tables
            WHERE table_name=\'mid_questions\'
        );
        """)

    if not cursor.fetchone()[0]:
        if DEBUG:
            print("Creating table mid_questions")

        cursor.execute(
            """
            CREATE TABLE mid_questions (
                mid_question_id SERIAL2 PRIMARY KEY,
                mid_question_text VARCHAR(255) NOT NULL,
                mid_question_ans VARCHAR(255) NOT NULL,
                course_id INT2 NOT NULL,
                CONSTRAINT fk_course_id
                    FOREIGN KEY(course_id)
                    REFERENCES courses(course_id)
                    ON DELETE CASCADE
                    ON UPDATE CASCADE
            );
            """)

        for mid_question in courses_data["mid_questions"]:
            columns = list(mid_question.keys())
            values = list(mid_question.values())
            query = sql.SQL("INSERT INTO mid_questions({}) VALUES({}) \
                             RETURNING mid_question_id;").format(
                        sql.SQL(", ").join(map(sql.Identifier, columns)),
                        sql.SQL(", ").join(map(sql.Literal, values)),
                    )

            cursor.execute(query)

    # Check the existence of "test_steps" table (and create it).
    cursor.execute(
        """
        SELECT EXISTS(
            SELECT * FROM information_schema.tables
            WHERE table_name=\'test_steps\'
        );
        """)

    if not cursor.fetchone()[0]:
        if DEBUG:
            print("Creating table test_steps")

        cursor.execute(
            """
            CREATE TABLE test_steps (
                test_step_id SERIAL2 PRIMARY KEY,
                test_step_inner_id INT2 NOT NULL,
                test_step_text VARCHAR(255) NOT NULL,
                test_step_ans VARCHAR(255) NOT NULL,
                course_id INT2 NOT NULL,
                CONSTRAINT fk_course_id
                    FOREIGN KEY(course_id)
                    REFERENCES courses(course_id)
                    ON DELETE CASCADE
                    ON UPDATE CASCADE
            );
            """)

        for test_step in courses_data["test_steps"]:
            columns = list(test_step.keys())
            values = list(test_step.values())
            query = sql.SQL("INSERT INTO test_steps({}) VALUES({}) \
                             RETURNING test_step_id;").format(
                        sql.SQL(", ").join(map(sql.Identifier, columns)),
                        sql.SQL(", ").join(map(sql.Literal, values)),
                    )

            cursor.execute(query)

    # Check the existence of "users" table (and create it).
    cursor.execute(
        """
        SELECT EXISTS(
            SELECT * FROM information_schema.tables WHERE table_name=\'users\'
        );
        """)

    if not cursor.fetchone()[0]:
        if DEBUG:
            print("Creating table users")

        cursor.execute(
            """
            CREATE TABLE users (
                user_id INT PRIMARY KEY,
                user_name VARCHAR(255) NOT NULL,
                user_step INT2 NOT NULL DEFAULT 0,
                user_score INT2 NOT NULL DEFAULT 0,
                course_id INT2,
                user_test_started BOOL NOT NULL DEFAULT FALSE,
                CONSTRAINT fk_course_id
                    FOREIGN KEY(course_id)
                    REFERENCES courses(course_id)
                    ON DELETE CASCADE
                    ON UPDATE CASCADE
            );
            """)

    cursor.close()
    CONN.commit()

@app.route("/api/user", methods=["GET"])
def user_get():
    """
    Get information from the database about an user, given his id. If there are
    field names received in the body, only those will be queried. If no field is
    provided, every field will be selected. The body should be a JSON object
    following the schema:
    {
        "user_id": id,
        "fields": ["field1", ...]
    }

    Returns:
        Response: - 200 in case of success and the user info in the body.
                  - 400 if the body does not have all the necessary information
                  or the field names are wrong.
                  - 404 if the user is not found.
    """

    body_schema = {
        "type": "object",
        "properties": {
            "user_id": {"type": "number"},
            "fields": {
                "type": "array",
                "minItems": 1,
                "items": {
                    "type": "string",
                }
            }
        },
        "required": ["user_id"]
    }

    payload = request.get_json(silent=True)

    is_valid = validate_json(payload, body_schema)
    if not is_valid:
        return Response(status=400)

    user_id = payload["user_id"]

    if "fields" in payload:
        fields = payload["fields"]
        query = sql.SQL("SELECT {} FROM users WHERE user_id={};").format(
                    sql.SQL(", ").join(map(sql.Identifier, fields)),
                    sql.Literal(user_id)
                )
    else:
        query = sql.SQL("SELECT * FROM users WHERE user_id={};").format(
                    sql.Literal(payload["user_id"])
                )

    cursor = CONN.cursor(cursor_factory=RealDictCursor)

    try:
        cursor.execute(query)
        results = cursor.fetchall()
    except psycopg2.errors.UndefinedColumn:
        CONN.rollback()
        return Response(status=400)
    finally:
        cursor.close()

    CONN.commit()

    if len(results) == 0:
        return Response(status=404)

    return Response(
        status=200,
        response=json.dumps(results),
        mimetype="application/json"
    )

@app.route("/api/user", methods=["POST"])
def user_add():
    """
    Add a new user to the database. The information is received in the body of
    the request and should be a JSON object following the schema:
    {
        "user_id": id,
        "user_name": "name"
    }

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

    query = sql.SQL("INSERT INTO users(user_id, user_name) \
                     VALUES ({}, {});").format(
                sql.Literal(payload["user_id"]),
                sql.Literal(payload["user_name"])
            )

    cursor = CONN.cursor()

    try:
        cursor.execute(query)
    except psycopg2.errors.UniqueViolation:
        CONN.rollback()
        return Response(status=409)
    except psycopg2.DataError:
        CONN.rollback()
        return Response(
            status=400,
            response="values",
            mimetype="text/plain"
        )
    finally:
        cursor.close()

    CONN.commit()

    return Response(status=201)

@app.route("/api/user", methods=["PUT"])
def user_update():
    """
    Update the information about a user in the database, given his id. Only the
    fields provided in the body will be updated, with their respective values.
    The body should be a JSON object following the schema:
    {
        "user_id": id,
        "col_name1": value1,
        ...
        "returning": ["col_name1", ...]
    }

    Returns:
        Response: - 200 in case of success.
                  - 400 + "fields" if the body does not have all the necessary
                  information or the field names are wrong.
                  - 400 + "values" if the values are out of bounds.
                  - 404 if the user is not found.
    """

    body_schema = {
        "type": "object",
        "properties": {
            "user_id": {"type": "number"},
            "user_name": {"type": "string"},
            "user_step": {"type": "number"},
            "user_score": {"type": "number"},
            "course_id": {"type": ["number", "null"]},
            "user_test_started": {"type": "boolean"},
            "returning": {
                "type": "array",
                "minItems": 1,
                "items": {
                    "type": "string",
                }
            }
        },
        "required": ["user_id"]
    }

    payload = request.get_json(silent=True)

    is_valid = validate_json(payload, body_schema)
    if not is_valid:
        return Response(
            status=400,
            response="fields",
            mimetype="text/plain"
        )

    user_id = payload["user_id"]

    if "returning" in payload:
        returning = payload["returning"]
        del payload["returning"]
    else:
        returning = ["user_id"]

    if len(payload) == 1:
        return Response(
            status=400,
            response="fields",
            mimetype="text/plain"
        )

    fields = payload.keys()
    values = payload.values()
    query = sql.SQL("UPDATE users SET ({})=({}) WHERE user_id={} \
                     RETURNING {};").format(
                sql.SQL(", ").join(map(sql.Identifier, fields)),
                sql.SQL(", ").join(map(sql.Literal, values)),
                sql.Literal(user_id),
                sql.SQL(", ").join(map(sql.Identifier, returning)),
            )

    cursor = CONN.cursor()

    try:
        cursor.execute(query)
        results = cursor.fetchall()
    except psycopg2.DataError:
        CONN.rollback()
        return Response(
            status=400,
            response="values",
            mimetype="text/plain"
        )
    except psycopg2.errors.UndefinedColumn:
        CONN.rollback()
        return Response(
            status=400,
            response="fields",
            mimetype="text/plain"
        )
    finally:
        cursor.close()

    CONN.commit()

    if len(results) == 0:
        return Response(status=404)

    return Response(
        status=200,
        response=json.dumps(results),
        mimetype="application/json"
    )

@app.route("/api/user/<int:user_id>/score", methods=["PUT"])
def user_inc_score(user_id=None):
    """
    Increment a user's score.

    Returns:
        Response: - 200 if success.
                  - 400 if values overflow.
                  - 404 if the user is not found.
    """

    query = sql.SQL("UPDATE users SET user_score=user_score+1 WHERE user_id={} \
                     RETURNING user_id;").format(
                sql.Literal(user_id)
            )

    cursor = CONN.cursor()

    try:
        cursor.execute(query)
        results = cursor.fetchall()
    except psycopg2.DataError:
        CONN.rollback()
        return Response(status=400)
    finally:
        cursor.close()

    CONN.commit()

    if len(results) == 0:
        return Response(status=404)

    return Response(status=200)

@app.route("/api/user/<int:user_id>", methods=["DELETE"])
def user_del(user_id=None):
    """
    Delete an user from the database.

    Args:
        user_id (int): The user id received by the URL.
    Returns:
        Response: - 200 in case of success.
                  - 404 if the user is not found.
    """

    query = sql.SQL("DELETE FROM users WHERE user_id={} RETURNING 1;").format(
                sql.Literal(user_id),
            )

    cursor = CONN.cursor()
    cursor.execute(query)
    num_updates = len(cursor.fetchall())
    cursor.close()
    CONN.commit()

    if num_updates == 0:
        return Response(status=404)

    return Response(status=200)

@app.route("/api/courses", methods=["GET"])
def courses_get():
    """
    Retrieve the list of available courses.

    Returns:
        Response: - 200 in case of success and the list of courses in the body.
    """

    cursor = CONN.cursor(cursor_factory=RealDictCursor)

    query = sql.SQL("SELECT * FROM courses;")

    cursor.execute(query)
    results = cursor.fetchall()
    cursor.close()

    CONN.commit()

    return Response(
        status=200,
        response=json.dumps(results),
        mimetype="application/json"
    )

@app.route("/api/course", methods=["GET"])
def course_get():
    """
    Get information from the database about a course, given its id or name. If
    there are field names received in the body, only those will be queried. If
    no field is provided, every field will be selected. The body should be a
    JSON object following the schema:
    {
        "course_id": id OR "course_name": name,
        "fields": ["field1", ...]
    }

    Returns:
        Response: - 200 in case of success and the course info in the body.
                  - 400 if the body does not have all the necessary information
                  or the field names are wrong.
                  - 404 if the course is not found.
    """

    body_schema = {
        "type": "object",
        "properties": {
            "course_id": {"type": "number"},
            "course_name": {"type": "string"},
            "fields": {
                "type": "array",
                "minItems": 1,
                "items": {
                    "type": "string",
                }
            }
        },
        "oneOf": [
            {
                "required": [
                    "course_id"
                ]
            },
            {
                "required": [
                    "course_name"
                ]
            }
        ]
    }

    payload = request.get_json(silent=True)

    is_valid = validate_json(payload, body_schema)
    if not is_valid:
        return Response(status=400)

    if "course_id" in payload:
        cond_field = "course_id"
        val = payload["course_id"]
    else:
        cond_field = "course_name"
        val = payload["course_name"]

    if "fields" in payload:
        fields = payload["fields"]
        query = sql.SQL("SELECT {} FROM courses WHERE {}={};").format(
                    sql.SQL(", ").join(map(sql.Identifier, fields)),
                    sql.Identifier(cond_field),
                    sql.Literal(val)
                )
    else:
        query = sql.SQL("SELECT * FROM courses WHERE {}={};").format(
                    sql.Identifier(cond_field),
                    sql.Literal(val)
                )

    cursor = CONN.cursor(cursor_factory=RealDictCursor)

    try:
        cursor.execute(query)
        results = cursor.fetchall()
    except psycopg2.errors.UndefinedColumn:
        CONN.rollback()
        return Response(status=400)
    finally:
        cursor.close()

    CONN.commit()

    if len(results) == 0:
        return Response(status=404)

    return Response(
        status=200,
        response=json.dumps(results),
        mimetype="application/json"
    )

@app.route("/api/course_steps", methods=["GET"])
def course_step_get():
    """
    Retrieve a course step from the database.

    Returns:
        Response: - 200 in case of success and the step's object in the body.
                  - 400 if the body does not have all the necessary information.
                  - 404 if the step does not exist.
    """

    body_schema = {
        "type": "object",
        "properties": {
            "course_step_inner_id": {"type": "number"},
            "course_id": {"type": "number"}
        },
        "required": ["course_step_inner_id", "course_id"]
    }

    payload = request.get_json(silent=True)

    is_valid = validate_json(payload, body_schema)
    if not is_valid:
        return Response(status=400)

    step_id = payload["course_step_inner_id"]
    course_id = payload["course_id"]
    query = sql.SQL("SELECT * FROM course_steps \
                     WHERE course_step_inner_id={} AND course_id={};").format(
                sql.Literal(step_id),
                sql.Literal(course_id)
            )

    cursor = CONN.cursor(cursor_factory=RealDictCursor)

    cursor.execute(query)
    results = cursor.fetchall()
    cursor.close()

    CONN.commit()

    if len(results) == 0:
        return Response(status=404)

    return Response(
        status=200,
        response=json.dumps(results),
        mimetype="application/json"
    )

@app.route("/api/course_steps/max/<int:course_id>", methods=["GET"])
def course_step_max_get(course_id=None):
    """
    Retrieve the max inner id of a course step from the database, for a given
    course.

    Returns:
        Response: - 200 in case of success and the maximum id in the body.
                  - 404 if the step does not exist.
    """

    query = sql.SQL("SELECT MAX(course_step_inner_id) FROM course_steps \
                     WHERE course_id={};").format(
                sql.Literal(course_id)
            )

    cursor = CONN.cursor(cursor_factory=RealDictCursor)

    cursor.execute(query)
    results = cursor.fetchall()
    cursor.close()

    CONN.commit()

    if len(results) == 0:
        return Response(status=404)

    return Response(
        status=200,
        response=json.dumps(results),
        mimetype="application/json"
    )

@app.route("/api/mid_questions/<int:course_id>", methods=["GET"])
def mid_question_get(course_id=None):
    """
    Retrieve a course mid-course question from the database.

    Args:
        course_id (int): The current's course id.
    Returns:
        Response: - 200 in case of success and the step's object in the body.
                  - 404 if the question does not exist.
    """

    query = sql.SQL("SELECT * FROM mid_questions WHERE course_id={};").format(
                sql.Literal(course_id)
            )

    cursor = CONN.cursor(cursor_factory=RealDictCursor)

    cursor.execute(query, (course_id, ))
    results = cursor.fetchall()
    cursor.close()

    CONN.commit()

    if len(results) == 0:
        return Response(status=404)

    return Response(
        status=200,
        response=json.dumps(results),
        mimetype="application/json"
    )

@app.route("/api/test_steps", methods=["GET"])
def test_step_get_random():
    """
    Retrieve a course test step from the database. The step is randomly chosen
    from the pool.

    Returns:
        Response: - 200 in case of success and the step's object in the body.
                  - 400 if the body does not have all the necessary information.
                  - 404 if the step does not exist.
    """

    body_schema = {
        "type": "object",
        "properties": {
            "test_step_inner_id": {"type": "number"},
            "course_id": {"type": "number"}
        },
        "required": ["test_step_inner_id", "course_id"]
    }

    payload = request.get_json(silent=True)

    is_valid = validate_json(payload, body_schema)
    if not is_valid:
        return Response(status=400)

    step_id = payload["test_step_inner_id"]
    course_id = payload["course_id"]
    query = sql.SQL("SELECT * FROM test_steps \
                     WHERE test_step_inner_id={} AND course_id={} \
                     ORDER BY RANDOM() LIMIT 1;").format(
                sql.Literal(step_id),
                sql.Literal(course_id)
            )

    cursor = CONN.cursor(cursor_factory=RealDictCursor)

    cursor.execute(query)
    results = cursor.fetchall()
    cursor.close()

    CONN.commit()

    if len(results) == 0:
        return Response(status=404)

    return Response(
        status=200,
        response=json.dumps(results),
        mimetype="application/json"
    )

@app.route("/api/test_steps/<int:test_step_id>", methods=["GET"])
def test_step_get_exact(test_step_id=None):
    """
    Retrieve a course test step from the database given the test_step_id.

    Returns:
        Response: - 200 in case of success and the step's object in the body.
                  - 404 if the step does not exist.
    """

    query = sql.SQL("SELECT * FROM test_steps WHERE test_step_id={};").format(
                sql.Literal(test_step_id)
            )

    cursor = CONN.cursor(cursor_factory=RealDictCursor)

    cursor.execute(query)
    results = cursor.fetchall()
    cursor.close()

    CONN.commit()

    if len(results) == 0:
        return Response(status=404)

    return Response(
        status=200,
        response=json.dumps(results),
        mimetype="application/json"
    )

@app.route("/api/test_steps/max/<int:course_id>", methods=["GET"])
def test_step_max_get(course_id=None):
    """
    Retrieve the max inner id of a test step from the database, for a given
    course.

    Returns:
        Response: - 200 in case of success and the maximum id in the body.
                  - 404 if the step does not exist.
    """

    query = sql.SQL("SELECT MAX(test_step_inner_id) FROM test_steps \
                     WHERE course_id={};").format(
                sql.Literal(course_id)
            )

    cursor = CONN.cursor(cursor_factory=RealDictCursor)

    cursor.execute(query)
    results = cursor.fetchall()
    cursor.close()

    CONN.commit()

    if len(results) == 0:
        return Response(status=404)

    return Response(
        status=200,
        response=json.dumps(results),
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
                     <h1>This is the database adaptor.</h1>
                     </body>
                     </html> """,
        mimetype="text/html"
    )

if __name__ == "__main__":
    parser = ArgumentParser(description="Run an adapter to PostgreSQL.")
    parser.add_argument("-d", "--debug", action="store_true",
                    help="specify if additional debug output should be shown")
    args = parser.parse_args()

    DEBUG = args.debug
    db_adapt_port = int(os.getenv("DB_ADAPT_PORT", "5000"))
    db_adapt_addr = os.getenv("DB_ADAPT_ADDR", "0.0.0.0")

    CONN = init_postgres_con()
    populate_postgres()

    app.run(host=db_adapt_addr, port=db_adapt_port, debug=DEBUG)
