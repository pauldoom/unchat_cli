# Base docker image
FROM python:3.6-alpine

# Create service directory
WORKDIR /service

# Create user to run service under.   It's name is Snake Pliskin.
RUN adduser -S -h /service -H snake

# Copy requirements
COPY requirements.txt requirements.txt


RUN pip install --upgrade pip \
# Install service requirements
&& pip install -r requirements.txt --upgrade

# Application code
COPY unchat_cli.py unchat_cli.py

# Run as Snake
USER snake

# Start the CLI
CMD [ "python", "unchat_cli.py" ]
