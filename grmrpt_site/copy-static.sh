#!/bin/sh

cp -a /src/static/. /src/static_vol

exec "$@"