FROM wazopbx/wazo-plugind

COPY . /usr/src/wazo-plugind
WORKDIR /usr/src/wazo-plugind

ENV PYTHONDONTWRITEBYTECODE='disabled'

RUN python setup.py develop
