FROM python:3.8.10-slim
WORKDIR /tmp
COPY src/database_adapter/database_adapter.py .
COPY src/database_adapter/requirements.txt .
COPY courses.json .
SHELL ["/bin/bash", "-c"]
RUN python -m venv . && source bin/activate
RUN python -m pip install --upgrade pip
RUN python -m pip install -r requirements.txt
EXPOSE 5000
ENTRYPOINT ["python", "database_adapter.py"]
