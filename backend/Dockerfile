FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
ARG CACHEBUST=2
RUN pip install -r requirements.txt
COPY . .
RUN chmod +x start.sh
CMD ["/bin/bash", "./start.sh"]
