FROM python:3.8.10-slim
WORKDIR /tmp
COPY src/frontend_adapter/frontend_adapter.py .
COPY src/frontend_adapter/requirements.txt .
SHELL ["/bin/bash", "-c"]
RUN python -m venv . && source bin/activate
RUN python -m pip install --upgrade pip
RUN python -m pip install -r requirements.txt
ENTRYPOINT ["python", "frontend_adapter.py"]
