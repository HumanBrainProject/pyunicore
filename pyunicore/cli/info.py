from __future__ import annotations

import re

from pyunicore.cli.base import Base
from pyunicore.client import Resource


class Info(Base):
    def add_command_args(self):
        self.parser.prog = "unicore system-info"
        self.parser.description = self.get_synopsis()
        self.parser.add_argument("URL", help="Endpoint URL(s)", nargs="*")
        self.parser.add_argument(
            "-p",
            "--pattern",
            required=False,
            type=str,
            help="Only show info for endpoints matching the given regexp",
        )
        self.parser.add_argument(
            "-l", "--long", required=False, action="store_true", help="Show detailed info"
        )

    def _require_registry(self):
        return True

    def get_synopsis(self):
        return """Show information about endpoint(s). If no explicit endpoints are given,
        the endpoints in the registry are used. The optional pattern allows to limit which
        endpoints are listed."""

    def get_description(self):
        return "show info on available services"

    def get_group(self):
        return "Utilities"

    def run(self, args):
        super().setup(args)
        endpoints = self.registry.site_urls.values()

        if self.args.URL:
            endpoints = self.args.URL

        for url in endpoints:
            if self.args.pattern:
                if not re.match(self.args.pattern, url):
                    continue
            c = Resource(self.credential, resource_url=url)
            self.show_endpoint_details(c)

    def show_endpoint_details(self, ep: Resource):
        print(ep.resource_url)
        if ep.resource_url.endswith("/rest/core"):
            self._show_details_core(ep)
        elif re.match(".*/rest/core/storages/.+", ep.resource_url):
            self._show_details_storage(ep)
        else:
            print(" * no further details available.")

    def _show_details_core(self, ep: Resource):
        props = ep.properties
        print(" * type: UNICORE/X base")
        print(f" * server v{props['server']['version']}")
        xlogin = props["client"]["xlogin"]
        role = props["client"]["role"]["selected"]
        uid = xlogin.get("UID", "n/a")
        print(f" * authenticated as: '{props['client']['dn']}' role='{role}' uid='{uid}'")
        grps = xlogin.get("availableGroups", [])
        uids = xlogin.get("availableUIDs", [])
        if len(uids) > 0:
            print(f" * available UIDs: {uids}")
        if len(grps) > 0:
            print(f" * available groups: {grps}")
        roles = props["client"]["role"].get("availableRoles", [])
        if len(roles) > 0:
            print(f" * available roles: {roles}")

    def _show_details_storage(self, ep: Resource):
        props = ep.properties
        t = "storage"
        if ep.resource_url.endswith("-uspace"):
            t = t + " (job directory)"
        print(f" * type: {t}")
        print(f" * mount point: {props['mountPoint']}")
        print(f" * free space : {int(props['freeSpace']/1024/1024)} MB")
