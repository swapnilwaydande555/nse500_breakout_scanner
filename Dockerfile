FROM python:3.11-slim
WORKDIR /app
COPY . /app
RUN pip install --upgrade pip && pip install -r requirements.txt
EXPOSE 8080
# Streamlit runs on port 8080 in this container
CMD ["streamlit", "run", "app.py", "--server.port=8080", "--server.address=0.0.0.0"]
