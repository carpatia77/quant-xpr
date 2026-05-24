FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
ARG CACHEBUST=1
RUN pip install -r requirements.txt
COPY . .
RUN chmod +x start.sh
CMD ["/bin/bash", "./start.sh"]
