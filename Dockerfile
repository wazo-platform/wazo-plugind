FROM python:3.4.2

ADD . /usr/src/wazo-plugind
ADD ./contribs/docker/certs /usr/share/xivo-certs

WORKDIR /usr/src/wazo-plugind

RUN true \
    && pip install pyparsing \
    && pip install appdirs \
    && pip install -r requirements.txt \
    && adduser --quiet --system --group --home /var/lib/wazo-plugind wazo-plugind \
    && mkdir -p /etc/wazo-plugind/conf.d \
    && mkdir -p /var/run/wazo-plugind \
    && mkdir -p /var/lib/wazo-plugind/downloads \
    && mkdir -p /var/lib/wazo-plugind/plugins \
    && chown -R wazo-plugind:wazo-plugind /var/lib/wazo-plugind \
    && chmod 755 /var/lib/wazo-plugind \
    && chmod a+w /var/run/wazo-plugind \
    && touch /var/log/wazo-plugind.log \
    && chown wazo-plugind:wazo-plugind /var/log/wazo-plugind.log \
    && python setup.py install \
    && cp -r etc/* /etc

VOLUME ["/var/lib/wazo-plugind/plugins"]
EXPOSE 9503

CMD ["wazo-plugind"]
