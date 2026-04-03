FROM phusion/baseimage:0.11

ENV DEBIAN_FRONTEND=noninteractive

COPY etc/apt/sources.list /etc/apt/sources.list
RUN apt-get update; apt-get install -yy htop nginx php5-fpm php5-cli php5-gd php5-mysql sudo --no-install-recommends; apt-get clean; rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*

COPY ttrss /ttrss
COPY etc /etc
COPY service /etc/runit/runsvdir/default

EXPOSE 80

CMD ["/sbin/my_init"]
