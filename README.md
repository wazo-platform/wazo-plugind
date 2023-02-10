# wazo-plugind

[![Build Status](https://jenkins.wazo.community/buildStatus/icon?job=wazo-plugind)](https://jenkins.wazo.community/job/wazo-plugind)

A microservice to manage plugins in the [Wazo PBX](http://wazo.community).

wazo-plugind allows the administrator to manage plugins installed on a Wazo stack using
a simple HTTP interface.

## Docker

The official docker image for this service is `wazoplatform/wazo-plugind`.

### Getting the image

To download the latest image from the docker hub

```sh
docker pull wazoplatform/wazo-plugind
```

### Running wazo-plugind

```sh
docker run -e"XIVO_UUID=<the xivo UUID>" wazoplatform/wazo-plugind
```

### Building the image

Building the docker image:

```sh
docker build -t wazoplatform/wazo-plugind .
```
