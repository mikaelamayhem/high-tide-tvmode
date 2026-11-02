# secret_storage.py
#
# Copyright 2025 Nokse <nokse@posteo.com>
#
# This file is free software; you can redistribute it and/or modify it
# under the terms of the GNU Lesser General Public License as published by
# the Free Software Foundation; either version 3 of the License, or (at
# your option) any later version.
#
# This file is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or
# FITNESS FOR A PARTICULAR PURPOSE. See the GNU Lesser General Public
# License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>.
#
# SPDX-License-Identifier: LGPL-3.0-or-later

import json
import os
from typing import Any, Dict, Tuple

import tidalapi
from gi.repository import GLib

from .platform_info import IS_ANDROID

try:
    from gi.repository import Secret, Xdp
except ImportError:  # Android: no keyring service
    Secret = Xdp = None

import logging
logger = logging.getLogger(__name__)


class SecretStore:
    file_path: str | None = None

    def __init__(self, session: tidalapi.Session) -> None:
        super().__init__()

        logger.info("initializing secret store")

        self.version = "0.0"
        self.session: tidalapi.Session = session

        self.token_dictionary: Dict[str, str] = {}
        self.key: str = "high-tide-login"

        if IS_ANDROID or Secret is None:
            self._init_file_store()
            return

        self.attributes: Dict[str, Secret.SchemaAttributeType] = {
            "version": Secret.SchemaAttributeType.STRING
        }

        self.schema = Secret.Schema.new(
            "io.github.nokse22.high-tide", Secret.SchemaFlags.NONE, self.attributes
        )

        # Ensure the Login keyring is unlocked (https://github.com/Nokse22/high-tide/issues/97)
        # This is also only possible outside of a flatpak.
        if not Xdp.Portal.running_under_flatpak():
            service = Secret.Service.get_sync(Secret.ServiceFlags.NONE)
            if service:
                collection = Secret.Collection.for_alias_sync(
                    service, Secret.COLLECTION_DEFAULT, Secret.CollectionFlags.NONE
                )
                if collection and collection.get_locked():
                    logger.info("Collection is locked, attempting to unlock")
                    service.unlock_sync([collection])

        password = Secret.password_lookup_sync(self.schema, {}, None)
        try:
            if password:
                json_data = json.loads(password)
                self.token_dictionary = json_data

        except Exception:
            logger.exception("Failed to load secret store, resetting")

            self.token_dictionary = {}

    def get(self) -> Tuple[str, str, str]:
        """Get the stored authentication tokens.

        Returns:
            tuple: A tuple containing (token_type, access_token, refresh_token)
        """
        return (
            self.token_dictionary["token-type"],
            self.token_dictionary["access-token"],
            self.token_dictionary["refresh-token"],
        )

    def clear(self) -> None:
        """Clear all stored authentication tokens from memory and keyring.

        Removes tokens from the internal dictionary and deletes them from
        the system keyring/secret storage.
        """
        self.token_dictionary.clear()
        self.save()

        if self.file_path:
            try:
                os.remove(self.file_path)
            except FileNotFoundError:
                pass
            return

        Secret.password_clear_sync(self.schema, {}, None)

    def save(self, is_pkce: bool = False) -> None:
        """Save the current session tokens to secure storage.

        Stores the session's token_type, access_token, and refresh_token
        in the system keyring for persistent authentication.
        """
        token_type: str = self.session.token_type
        access_token: str = self.session.access_token
        refresh_token: str = self.session.refresh_token
        expiry_time: Any = self.session.expiry_time

        self.token_dictionary = {
            "token-type": token_type,
            "access-token": access_token,
            "refresh-token": refresh_token,
            "expiry-time": str(expiry_time),
            "is-pkce": is_pkce,
        }

        json_data: str = json.dumps(self.token_dictionary)

        if self.file_path:
            self._write_file(json_data)
            return

        Secret.password_store_sync(
            self.schema, {}, Secret.COLLECTION_DEFAULT, self.key, json_data, None
        )

    def _init_file_store(self) -> None:
        """Keep the tokens in a private file (used on Android).

        The GTK Android runtime replaces the app's internal files on every
        update, so this lives in the user data dir, which survives updates
        and is only readable by this app."""
        directory = os.path.join(GLib.get_user_data_dir(), "high-tide")
        os.makedirs(directory, mode=0o700, exist_ok=True)
        self.file_path = os.path.join(directory, "login.json")
        try:
            with open(self.file_path, encoding="utf-8") as f:
                self.token_dictionary = json.load(f)
        except FileNotFoundError:
            pass
        except Exception:
            logger.exception("Failed to load saved login, resetting")

    def _write_file(self, json_data: str) -> None:
        tmp = self.file_path + ".tmp"
        fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(json_data)
        os.replace(tmp, self.file_path)
