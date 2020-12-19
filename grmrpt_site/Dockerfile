FROM ubuntu
MAINTAINER Alex Philpott
# Update packages
RUN apt-get update -y

# Install Python Setuptools and some other fancy tools for working we this container if we choose to attach to it
RUN apt-get install -y tar git curl nano wget dialog net-tools build-essential
RUN apt-get install -y python3.6 python3-dev python3-pip python-distribute supervisor libmysqlclient-dev

# copy the contents of this directory over to the container at location /src
ADD . /src

# Add and install Python modules
RUN cd /src && pip3 install -r /src/requirements.txt
RUN mkdir -p /opt/python/log
WORKDIR /src