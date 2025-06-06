from __future__ import annotations

import argparse
import getpass
import json
import os
from base64 import b64decode

import pyunicore.client
import pyunicore.credentials


class Base:
    """Base command class with support for common commandline args"""

    def __init__(self, password_source=None):
        self.parser = argparse.ArgumentParser(
            prog="unicore", description="A commandline client for UNICORE"
        )
        self.config = {"verbose": False}
        self.args = None
        self.credential = None
        self.registry = None
        self.add_base_args()
        self.add_command_args()
        if password_source:
            self.password_source = password_source
        else:
            self.password_source = getpass.getpass

    def _value(self, value: str):
        if value.lower() == "true":
            return True
        if value.lower() == "false":
            return False
        return value

    def load_user_properties(self):
        with open(self.config_file) as f:
            for line in f.readlines():
                line = line.strip()
                if line.startswith("#"):
                    continue
                try:
                    key, value = line.split("=", 1)
                    self.config[key] = self._value(value)
                except ValueError:
                    pass

    def add_base_args(self) -> argparse._ArgumentGroup:
        general_options = self.parser.add_argument_group("General options")
        general_options.add_argument(
            "-v", "--verbose", required=False, action="store_true", help="Be verbose"
        )
        general_options.add_argument(
            "-c",
            "--configuration",
            metavar="CONFIG",
            default=f"{os.getenv('HOME')}/.ucc/properties",
            help="Configuration file",
        )
        return general_options

    def add_command_args(self):
        pass

    def setup(self, args):
        self.args = self.parser.parse_args(args)
        self.is_verbose = self.args.verbose
        self.config_file = self.args.configuration
        self.load_user_properties()
        self.create_credential()
        self.registry = self.create_registry()

    def get_description(self):
        return "N/A"

    def get_synopsis(self):
        return "N/A"

    def get_group(self):
        return "Other"

    def create_credential(self):
        auth_method = self.config.get("authentication-method", "USERNAME").upper()
        if "OIDC-AGENT" == auth_method:
            account_name = self.config.get("oidc-agent.account")
            self.credential = pyunicore.credentials.OIDCAgentToken(account_name)
        elif "OIDC-SERVER" == auth_method:
            self.credential = pyunicore.credentials.OIDCServerToken(self.config)
        elif "USERNAME" == auth_method:
            username = self.config["username"]
            password = self._get_password()
            self.credential = pyunicore.credentials.create_credential(username, password)
        elif "ANONYMOUS" == auth_method:
            self.credential = pyunicore.credentials.Anonymous()

    def _get_password(self, key="password") -> str:
        password = self.config.get(key)
        if password is None:
            _p = os.getenv("UCC_PASSWORD")
            if not _p:
                pwd_prompt = "Enter password: "
                password = self.password_source(pwd_prompt)
            else:
                password = _p
        return password

    def _require_registry(self) -> bool:
        return self.config.get("contact-registry", True)

    def create_registry(self) -> pyunicore.client.Registry | None:
        if self._require_registry():
            return pyunicore.client.Registry(self.credential, self.config["registry"])
        else:
            return None

    def verbose(self, msg):
        if self.is_verbose:
            print(msg)

    def human_readable(self, value, decimals=0):
        for unit in ["B", "KB", "MB", "GB"]:
            if value < 1024.0 or unit == "GB":
                break
            value /= 1024.0
        return f"{value:.{decimals}f} {unit}"


class IssueToken(Base):
    """Get an authentication token from a UNICORE server"""

    def add_command_args(self):
        self.parser.prog = "unicore issue-token"
        self.parser.description = self.get_synopsis()
        self.parser.add_argument("URL", help="Token endpoint URL", nargs="?")
        self.parser.add_argument("-s", "--sitename", required=False, type=str, help="Site name")
        self.parser.add_argument(
            "-l",
            "--lifetime",
            required=False,
            type=int,
            default=-1,
            help="Initial lifetime (in seconds) for token",
        )
        self.parser.add_argument(
            "-R",
            "--renewable",
            required=False,
            action="store_true",
            help="Token can be used to get a fresh token",
        )
        self.parser.add_argument(
            "-L",
            "--limited",
            required=False,
            action="store_true",
            help="Token should be limited to the issuing server",
        )
        self.parser.add_argument(
            "-I", "--inspect", required=False, action="store_true", help="Inspect the issued token"
        )

    def get_synopsis(self):
        return """Gets a JWT authentication token from a UNICORE token endpoint.
                  Lifetime and other properties can be configured."""

    def get_description(self):
        return "issue an authentication token"

    def get_group(self):
        return "Utilities"

    def run(self, args):
        super().setup(args)
        site_name = self.args.sitename
        if site_name:
            if self.registry:
                endpoint = self.registry.site_urls[site_name]
            else:
                raise ValueError(
                    "Sitename resolution requires registry - please check your configuration!"
                )
        else:
            endpoint = self.args.URL
        if not endpoint:
            raise ValueError("Either URL or --sitename must be given.")
        endpoint = endpoint.split("/token")[0]
        token = self.issue_token(
            url=endpoint,
            lifetime=self.args.lifetime,
            limited=self.args.limited,
            renewable=self.args.renewable,
        )
        if self.args.inspect:
            self.show_token_details(token)
        print(token)

    def issue_token(self, url: str, lifetime: int, limited: bool, renewable: bool) -> str:
        client = pyunicore.client.Client(self.credential, site_url=url)
        return client.issue_auth_token(lifetime, renewable, limited)

    def show_token_details(self, token: str):
        _p = token.split(".")[1]
        _p += "=" * (-len(_p) % 4)  # padding
        payload = json.loads(b64decode(_p))
        print(f"Subject:      {payload['sub']}")
        print(f"Lifetime (s): {payload['exp'] - payload['iat']}")
        print(f"Issued by:    {payload['iss']}")
        print(f"Valid for:    {payload.get('aud', '<unlimited>')}")
        print(f"Renewable:    {payload.get('renewable', 'no')}")


class REST(Base):
    """Low-level REST API operations (GET, PUT, POST, DELETE)"""

    def add_command_args(self):
        self.parser.prog = "unicore rest"
        self.parser.description = self.get_synopsis()
        self.parser.add_argument("command", help="Operation (GET, PUT, POST, DELETE)")
        self.parser.add_argument("URL", help="Endpoint URL(s)", nargs="*")
        self.parser.add_argument(
            "-A",
            "--accept",
            required=False,
            default="application/json",
            help="Value for the 'Accept' header (default: 'application/json')",
        )
        self.parser.add_argument(
            "-C",
            "--content-type",
            required=False,
            default="application/json",
            help="Value for the 'Content-Type' header (default: 'application/json')",
        )
        self.parser.add_argument(
            "-i",
            "--include",
            required=False,
            action="store_true",
            help="Include the response headers in the output",
        )
        self.parser.add_argument("-D", "--data", required=False, help="JSON data for PUT/POST")

    def get_synopsis(self):
        return """Low-level REST API operations."""

    def get_description(self):
        return "perform a low-level REST API operation"

    def get_group(self):
        return "Utilities"

    def run(self, args):
        super().setup(args)
        cmd = self.args.command
        if not cmd:
            raise ValueError("REST operation (GET, PUT, POST, DELETE) required.")
        _headers = {"Accept": self.args.accept, "Content-Type": self.args.content_type}
        for endpoint in self.args.URL:
            self.verbose(f"HTTP {cmd} {endpoint}")
            self.to_json = "application/json" in self.args.accept
            tr = pyunicore.client.Transport(credential=self.credential, use_security_sessions=False)
            if "GET".startswith(cmd.upper()):
                response = tr.get(to_json=False, url=endpoint, headers=_headers)
            elif "POST".startswith(cmd.upper()):
                response = tr.post(url=endpoint, headers=_headers, data=self._read_data())
            elif "PUT".startswith(cmd.upper()):
                response = tr.put(url=endpoint, headers=_headers, data=self._read_data())
            elif "DELETE".startswith(cmd.upper()):
                response = tr.delete(url=endpoint)
            else:
                raise ValueError("Unsupported operation '%s'" % cmd)
            if response:
                self._print_response(response)

    def _print_response(self, response, print_body=True):
        if self.args.include:
            self._print_headers(response)
        if response.headers.get("Location"):
            self._last_location = response.headers["Location"]
            print(self._last_location)
        if print_body and response.status_code not in [201, 204]:
            if self.to_json:
                print(json.dumps(response.json(), indent=2))
            else:
                print(response.content)

    def _print_headers(self, response):
        print(f"HTTP/1.1 {response.status_code} {response.reason}")
        for h in response.headers:
            print(f"{h}: {response.headers[h]}")

    def _read_data(self):
        if self.args.data:
            d = self.args.data
            if d.startswith("@"):
                with open(d[1:]) as f:
                    d = f.read()
            return d
        else:
            return None
