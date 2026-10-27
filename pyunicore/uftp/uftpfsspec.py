import fsspec.implementations.ftp as ftpfs

import pyunicore.credentials as uc_credentials
from pyunicore.uftp.uftp import UFTP


class UFTPFS(ftpfs.FTPFileSystem):
    """A UFTP (UNICORE FTP) Filesystem.

    This extends the fsspec.implementations.ftp.FTPFileSystem
    with UFTP authentication.

    Example: create with auth URL and username/password credentials

    import fsspec

    fs = fsspec.filesystem('uftp',
            auth_url="https://localhost:9000/rest/auth/TEST",
            base_path="/opt/shared-data/",
            username="demouser",
            password="test123")


    """

    def __init__(
        self, auth_url, base_path="/", username=None, password=None, token=None, identity=None
    ):
        """Creates a new UFTP FS instance authenticating using the given URL and credentials"""
        self.uftp_auth_credentials = uc_credentials.create_credential(
            username, password, token, identity
        )
        self.uftp_auth_url = auth_url
        self.uftp_host, self.uftp_port, self.uftp_password = UFTP().authenticate(
            self.uftp_auth_credentials, auth_url, base_path
        )
        super().__init__(
            self.uftp_host, port=self.uftp_port, username="anonymous", password=self.uftp_password
        )
        self.base_path = base_path

    @classmethod
    def _strip_protocol(cls, path):
        return super(ftpfs.FTPFileSystem, cls)._strip_protocol(path)
