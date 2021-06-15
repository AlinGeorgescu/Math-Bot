FROM python:3.8.10-slim
WORKDIR /tmp
COPY src/math_bot/math_bot.py .
COPY src/math_bot/requirements.txt .
COPY src/math_bot/model model
SHELL ["/bin/bash", "-c"]
RUN python -m venv . && source bin/activate
RUN python -m pip install --upgrade pip
RUN python -m pip install -r requirements.txt
RUN python -m pip install -r model/requirements.txt
EXPOSE 5001
ENTRYPOINT ["python", "math_bot.py"]
