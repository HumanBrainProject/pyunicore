from collections import OrderedDict
from os import getenv

from fs.ftpfs import FTPFS
from fs.opener import Opener

import pyunicore.credentials as uc_credentials
from pyunicore.uftp.uftp import UFTP


class UFTPFS(FTPFS):
    """A UFTP (UNICORE FTP) Filesystem.

    This extends the fs.ftpfs.FTPFS filesystem
    with UFTP authentication.

    Example: create with auth URL and username/password credentials

      from pyunicore.credentials import UsernamePassword
      from pyunicore.uftp.uftpfs import UFTPFS

      auth = "https://localhost:9000/rest/auth/TEST"
      creds = UsernamePassword("demouser", "test123")
      base_path = "/"

      uftp_fs = UFTPFS(auth, creds, base_path)
      uftp_fs.tree()

    Example: create with URL

      from fs import open_fs
      fs_url = "uftp://demouser:test123@localhost:9000/rest/auth/TEST:/opt/shared-data"
      uftp_fs = open_fs(fs_url)
      uftp_fs.tree()


    """

    def __init__(self, auth_url, creds, base_path="/"):
        """Creates a new UFTP FS instance authenticating using the given URL and credentials"""
        self.uftp_host, self.uftp_port, self.uftp_password = UFTP().authenticate(
            creds, auth_url, base_path
        )
        super().__init__(
            self.uftp_host, port=self.uftp_port, user="anonymous", passwd=self.uftp_password
        )
        self.base_path = base_path

    def hassyspath(self, path):
        return False

    def validatepath(self, path):
        return "." + super().validatepath(path)

    # work around for bug in FPTFS - _read_dir() should never be used
    def _read_dir(self, path):
        return OrderedDict({})

    def __repr__(self):
        return f"UFTPFS({self.host!r}, port={self.port!r}), base_path={self.base_path!r}"

    __str__ = __repr__


class UFTPOpener(Opener):
    """Defines the Opener class used to open UFTP FS instances based on a URL"""

    protocols = ["uftp"]

    def _parse(self, resource_url):
        tok = resource_url.split("/rest/")
        auth_url = "https://" + tok[0]
        tok2 = tok[1].split(":")
        auth_url = auth_url + "/rest/" + tok2[0]
        base_dir = tok2[1] if len(tok) > 1 else "/"
        return auth_url, base_dir

    def _read_token(self, token_spec):
        token = None
        if token_spec:
            if token_spec.startswith("@@"):
                env_name = token_spec[2:]
                token = getenv(env_name, None)
            elif token_spec.startswith("@"):
                file_name = token_spec[1:]
                with open(file_name) as f:
                    token = f.read().strip()
            else:
                token = token_spec
        return token

    def _create_credential(self, parse_result):
        token = self._read_token(parse_result.params.get("token", None))
        return uc_credentials.create_credential(
            username=parse_result.username,
            password=parse_result.password,
            token=token,
            identity=parse_result.params.get("identity", None),
        )

    def open_fs(self, fs_url, parse_result, writeable, create, cwd):
        auth_url, base_dir = self._parse(parse_result.resource)
        cred = self._create_credential(parse_result)
        return UFTPFS(auth_url, cred, base_dir)
