FROM python:3.7
RUN apt-get update && apt-get install -y gcc musl-dev g++ && apt-get clean
RUN pip install -U pip Cython wheel setuptools
COPY requirements.txt /tmp/
RUN pip install -r /tmp/requirements.txt
RUN mkdir -p /app/oncall_slackbot /app/slacker_blocks /training
ENV PYTHONPATH=/app
# Set to paths that can be volume mounted
ENV SLACK_MODEL_DATA_PATH=/training/slack_channel_data
ENV SLACK_MODEL_OUTPUT_PATH=/training/slack_channel_model
ADD oncall_slackbot /app/oncall_slackbot
ADD slacker_blocks /app/slacker_blocks
