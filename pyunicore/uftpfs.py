""" UFTP extension to the pyfilesystem FTPFS class """
from fs.ftpfs import FTPFS
from fs.opener import Opener

import pyunicore.credentials as uc_credentials
from pyunicore.uftp import UFTP


class UFTPFS(FTPFS):
    """A UFTP (UNICORE FTP) Filesystem.

    This extends the fs.ftpfs.FTPFS filesystem
    with UFTP authentication.

    Example: create with auth URL and username/password credentials

      from pyunicore.credentials import UsernamePassword
      from pyunicore.uftpfs import UFTPFS

      auth = "https://localhost:9000/rest/auth/TEST
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
        uftp_host, uftp_port, uftp_password = UFTP().authenticate(creds, auth_url, base_path)
        super().__init__(uftp_host, port=uftp_port, user="anonymous", passwd=uftp_password)
        self.base_path = base_path

    def hassyspath(self, path):
        return False

    def validatepath(self, path):
        path = super().validatepath(path)
        if path.startswith("/"):
            path = "./" + path
        return path

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

    def open_fs(self, fs_url, parse_result, writeable, create, cwd):
        auth_url, base_dir = self._parse(parse_result.resource)
        cred = uc_credentials.create_credential(
            username=parse_result.username,
            password=parse_result.password,
            token=parse_result.params.get("token", None),
            identity=parse_result.params.get("identity", None),
        )
        return UFTPFS(auth_url, cred, base_dir)
