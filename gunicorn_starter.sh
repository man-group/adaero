#!/bin/sh

gunicorn --paste /usr/src/app/adaero/example.ini -w 2 --threads 2 -b 0.0.0.0:8080