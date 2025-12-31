# Copyright 2018-2025 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

import logging
import re
from typing import Any

from marshmallow import ValidationError

from wazo_plugind.db import PluginDB
from wazo_plugind.exceptions import PluginAlreadyInstalled, PluginValidationException
from wazo_plugind.schema import PluginMetadataSchema as _PluginMetadataSchema

logger = logging.getLogger(__name__)

Errors = dict[str, Any]


class Validator:
    valid_namespace = re.compile(r"^[a-z0-9]+$")
    valid_name = re.compile(r"^[a-z0-9-]+$")
    required_fields = ["name", "namespace", "version"]

    def __init__(self, plugin_db, current_wazo_version, install_params):
        self._db = plugin_db
        self._current_wazo_version = current_wazo_version
        self._install_params = install_params

        class PluginMetadataSchema(_PluginMetadataSchema):
            current_version = self._current_wazo_version

        self._PluginMetadataSchema = PluginMetadataSchema

    def validate(self, metadata):
        logger.debug("Using current version %s", self._current_wazo_version)
        logger.debug(
            "max_wazo_version: %s", metadata.get("max_wazo_version", "undefined")
        )

        try:
            body = self._PluginMetadataSchema().load(metadata)
        except ValidationError as e:
            raise PluginValidationException(e.messages)
        logger.debug("validated metadata: %s", body)

        if self._install_params["reinstall"]:
            return

        if self._db.is_installed(
            metadata["namespace"], metadata["name"], metadata["version"]
        ):
            raise PluginAlreadyInstalled(metadata["namespace"], metadata["name"])

    @classmethod
    def new_from_config(cls, config, current_wazo_version, install_params):
        plugin_db = PluginDB(config)
        return cls(plugin_db, current_wazo_version, install_params)
