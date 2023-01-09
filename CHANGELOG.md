# Changelog

## 23.01

* Bus configuration keys changed:

  * key `exchange_name` now defaults to `wazo-headers`
  * key `exchange_type` was removed

## 22.14

* New resource added `GET /status`

## 20.09

* Deprecate SSL configuration

## 18.03

* It is now possible to force the reinstallation of a plugin on `POST /plugins`
  with query parameter `reinstall=True`.

## 18.02

API version 0.1 has been removed

## 17.12

* New resource added `GET /market/<namespace>/<name>`
* New resource added `GET /plugins/<namespace>/<name>`
* The `url` parameter is now ignored when doing market installation

## 17.11

* REST API Version `0.1` has been deprecated and will be removed in Wazo `18.02`
* REST API Version `0.2` has been added with the following changes

  * `POST /plugins` does not have a `url` parameter has top level argument in its body
  * `POST /plugins` now requires an `url` parameter in its options field when using the `git` method
  * `POST /plugins` now accepts an `url` parameter in its options fields when using the `market` method

Example:

```sh
   # Version 0.1
   curl -X POST --header 'Content-Type: application/json' --header 'Accept: application/json' -d '{ \
     "url": "https://git.example.com/repo.git", \
     "method": "git", \
     "options": {"ref": "v1"} \
   }' 'https://wazo.example.com:9503/0.1/plugins'

   # Version 0.2
   curl -X POST --header 'Content-Type: application/json' --header 'Accept: application/json' -d '{ \
     "method": "git", \
     "options": {"ref": "v1", "url": "https://git.example.com/repo.git"} \
   }' 'https://wazo.example.com:9503/0.2/plugins'
```

## 17.10

* New endpoint for the plugin market

  * `GET /market`

* Added the `market` install method to `POST /plugins`

## 17.09

* `POST /plugins` now accepts an `options` parameter for method specific arguments

## 17.08

* `POST /plugins` and `DELETE /plugins` are now asynchronous

## 17.07

* New endpoint for plugins

  * `POST /plugins`
  * `GET /plugins`
  * `DELETE /plugins/<namespace>/<name>`

## 17.05

* New endpoint to fetch the configuration:

  * `GET /config`
