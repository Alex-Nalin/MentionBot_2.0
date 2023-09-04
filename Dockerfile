FROM python:3.10-alpine3.18

WORKDIR /app

COPY . .

# Install system dependencies
RUN apk add build-base linux-headers

# Install Python dependencies
RUN pip install --no-cache-dir psutil
RUN pip install --no-cache-dir -r requirements.txt

# Set the UID and GID for the myuser user
RUN adduser -D -u 2000 myuser

# Change ownership of all files to the myuser user
RUN chown -R myuser:myuser /app

#RUN groupadd -r -g 2000 mygrp && useradd -u 2000 -r -g mygrp myuser

USER myuser

CMD [ "python", "main.py" ]