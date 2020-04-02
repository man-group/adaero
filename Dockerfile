FROM ubuntu:18.04

WORKDIR /usr/src/app
COPY install-packages.sh .
RUN ./install-packages.sh
RUN curl https://bootstrap.pypa.io/get-pip.py | python3.6
COPY setup.py .
RUN pip3.6 install -e .
COPY feedback_tool feedback_tool
COPY gunicorn_starter.sh .

EXPOSE 8080
ENTRYPOINT ["./gunicorn_starter.sh"]
