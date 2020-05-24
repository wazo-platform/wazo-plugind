FROM python:3.7-slim-buster AS compile-image
LABEL maintainer="Wazo Maintainers <dev@wazo.community>"

RUN python -m venv /opt/venv
# Activate virtual env
ENV PATH="/opt/venv/bin:$PATH"

RUN apt-get -q update
RUN apt-get -yq install gcc

COPY . /usr/src/wazo-plugind
WORKDIR /usr/src/wazo-plugind
RUN pip install -r requirements.txt
RUN python setup.py install

RUN pip install pyparsing
RUN pip install appdirs

FROM python:3.7-slim-buster AS build-image
COPY --from=compile-image /opt/venv /opt/venv

COPY ./etc/wazo-plugind /etc/wazo-plugind
COPY ./templates /usr/lib/wazo-plugind/templates

RUN true \
    && apt-get -q update \
    && apt-get -yq install apt-utils fakeroot gdebi-core git wget gnupg \
    && adduser --quiet --system --group --home /var/lib/wazo-plugind wazo-plugind \
    && mkdir -p /etc/wazo-plugind/conf.d \
    && install -m 755 -d -o wazo-plugind -g wazo-plugind /var/lib/wazo-plugind/rules \
    && install -d -o wazo-plugind -g wazo-plugind /var/lib/wazo-plugind/downloads \
    && install -d -o wazo-plugind -g wazo-plugind /run/wazo-plugind/ \
    && install -o wazo-plugind -g wazo-plugind /dev/null /var/log/wazo-plugind.log \
    && chown -R wazo-plugind:wazo-plugind /usr/lib/wazo-plugind \
    && rm -rf /var/lib/apt/lists/*

EXPOSE 9503

# Activate virtual env
ENV PATH="/opt/venv/bin:$PATH"
CMD ["wazo-plugind"]
