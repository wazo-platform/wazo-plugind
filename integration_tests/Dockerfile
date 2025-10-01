FROM wazoplatform/wazo-plugind

COPY . /usr/src/wazo-plugind
WORKDIR /usr/src/wazo-plugind

# Mounted volume won't have same owner than container
RUN echo "[safe]\ndirectory = *" > /etc/gitconfig

ENV PYTHONDONTWRITEBYTECODE='true'

RUN python3 -m pip install -e .
