FROM python:3.7-buster

ADD . /usr/src/wazo-plugind
ADD ./contribs/docker/certs /usr/share/xivo-certs

WORKDIR /usr/src/wazo-plugind

RUN true \
    && apt-get update \
    && apt-get -yqq install apt-utils fakeroot gdebi-core git \
    && pip install pyparsing \
    && pip install appdirs \
    && pip install -r requirements.txt \
    && adduser --quiet --system --group --home /var/lib/wazo-plugind wazo-plugind \
    && mkdir -p /etc/wazo-plugind/conf.d \
    && mkdir -p /run/wazo-plugind \
    && mkdir -p /var/lib/wazo-plugind/downloads \
    && mkdir -p /var/lib/wazo-plugind/rules \
    && chown -R wazo-plugind:wazo-plugind /var/lib/wazo-plugind \
    && chmod 755 /var/lib/wazo-plugind/rules \
    && chmod 755 /var/lib/wazo-plugind \
    && chmod a+w /run/wazo-plugind \
    && touch /var/log/wazo-plugind.log \
    && chown wazo-plugind:wazo-plugind /var/log/wazo-plugind.log \
    && python setup.py install \
    && cp -r etc/* /etc \
    && mkdir -p /usr/lib/wazo-plugind \
    && cp -r templates /usr/lib/wazo-plugind \
    && chown -R wazo-plugind:wazo-plugind /usr/lib/wazo-plugind \
    && apt-get -yqq autoremove

EXPOSE 9503

CMD ["wazo-plugind"]
