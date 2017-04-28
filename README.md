# wazo-plugind

[![Build Status](https://travis-ci.org/wazo-pbx/wazo-plugind.svg?branch=master)](https://travis-ci.org/wazo-pbx/wazo-plugind)

A micro service to manage plugins in the [Wazo PBX](http://wazo.community).


wazo-plugind allow the administrator to manage plugins installed on a Wazo using
a simple HTTP interface.


## Docker

The official docker image for this service is `wazopbx/wazo-plugind`.


### Getting the image

To download the latest image from the docker hub

```sh
docker pull wazopbx/wazo-plugind
```


### Running wazo-plugind

```sh
docker run -e"XIVO_UUID=<the xivo UUID>" --cap-add LINUX_IMMUTABLE wazopbx/wazo-plugind
```

### Building the image

Building the docker image:

```sh
docker build -t wazopbx/wazo-plugind .
```
