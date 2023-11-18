FROM python:buster

WORKDIR /planner

RUN apt update
RUN apt install -y build-essential
RUN apt install -y python3-dev
RUN apt install -y libmariadb-dev
RUN apt install -y mariadb-client
RUN apt install -y pandoc
RUN apt install -y texlive-full

COPY requirements.txt requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY app app
COPY migrations migrations
COPY main.py config.py boot.sh ./
RUN chmod +x boot.sh

EXPOSE 5001

ENTRYPOINT ["./boot.sh"]
