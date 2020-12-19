FROM nginx

RUN rm -rf /usr/share/nginx/html/*
RUN mkdir -p /etc/nginx/html
RUN mkdir -p /var/log/nginx/healthd

COPY  ./default.conf  /etc/nginx/conf.d/default.conf
COPY  ./healthd.conf  /etc/httpd/conf.d/healthd.conf