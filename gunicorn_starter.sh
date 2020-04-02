#!/bin/sh

gunicorn --paste /usr/src/app/feedback_tool/example.ini -w 2 --threads 2 -b 0.0.0.0:8080