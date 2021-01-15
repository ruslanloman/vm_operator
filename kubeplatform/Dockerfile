FROM python:3.7

WORKDIR /src

ADD . /src

RUN pip install -r requirements.txt

CMD ["/usr/local/bin/python", "-u", "/usr/local/bin/kopf", "run", "main.py", "--verbose", "--log-format", "plain"]
