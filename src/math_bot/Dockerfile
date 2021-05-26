FROM python:3.8
WORKDIR /tmp
COPY src/math_bot/math_bot.py .
COPY src/math_bot/requirements.txt .
RUN python -m pip install --upgrade pip
RUN python -m pip install -r requirements.txt
EXPOSE 5001
ENTRYPOINT ["python", "math_bot.py"]
