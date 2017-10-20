FROM wazopbx/wazo-plugind

COPY . /usr/src/wazo-plugind
WORKDIR /usr/src/wazo-plugind

ENV PYTHONDONTWRITEBYTECODE='true'

RUN python setup.py develop

CMD ["wazo-plugind", "-d"]
