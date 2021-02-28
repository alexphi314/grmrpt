#!/bin/sh

cp -a /src/static/. /src/static_vol
python3 /src/manage.py migrate --noinput

exec "$@"