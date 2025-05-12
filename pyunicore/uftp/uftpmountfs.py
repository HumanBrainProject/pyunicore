import subprocess
from os import getenv

from fs.opener import Opener
from fs.osfs import OSFS

import pyunicore.credentials as uc_credentials
from pyunicore.uftp.uftp import UFTP


class UFTPMOUNTFS(OSFS):
    """A UFTP (UNICORE FTP) Filesystem which tries to mount the remote file system
    and then access it locally.

    This extends the fs.osfs.OSFS filesystem
    with UFTP authentication.

    Example: create with auth URL and username/password credentials

      from pyunicore.credentials import UsernamePassword
      from pyunicore.uftp.uftpmountfs import UFTPMOUNTFS

      auth = "https://localhost:9000/rest/auth/TEST"
      creds = UsernamePassword("demouser", "test123")
      base_path = "/"
      mount_dir = "/data/mount"

      uftp_mount_fs = UFTPMOUNTFS(auth, creds, base_path, mount_dir)
      uftp_mount_fs.tree()

    Example: create with URL

      from fs import open_fs
      fs_url = "uftpmount://demouser:test123@localhost:9000/rest/auth/TEST:/opt/shared-data==/mnt"
      uftp_fs = open_fs(fs_url)
      uftp_fs.tree()
    """

    def __init__(self, auth_url, creds, base_path="/", mount_dir="./uftp_mount"):
        """Creates a new UFTP FS instance authenticating using the given URL and credentials"""
        self.host, self.port, self.uftp_password = UFTP().authenticate(creds, auth_url, base_path)
        self.base_path = base_path
        self.mount_dir = mount_dir
        self._ensure_unmount()
        self._run_fusedriver(self.uftp_password)
        super().__init__(mount_dir)

    def close(self):
        self._ensure_unmount()
        super().close()

    def _ensure_unmount(self):
        """
        Unmounts the requested directory
        """
        cmd = "fusermount -u '%s'" % self.mount_dir
        return self._run_command(cmd)

    def _run_fusedriver(self, pwd):
        cmds = [
            "export UFTP_PASSWORD=%s" % pwd,
            f"python3 -m pyunicore.uftp.uftpfuse {self.host}:{self.port} '{self.mount_dir}'",
        ]
        cmd = ""
        for c in cmds:
            cmd += c + "\n"
        return self._run_command(cmd)

    def _run_command(self, cmd):
        try:
            raw_output = subprocess.check_output(
                cmd, shell=True, bufsize=4096, stderr=subprocess.STDOUT
            )
            exit_code = 0
        except subprocess.CalledProcessError as cpe:
            raw_output = cpe.output
            exit_code = cpe.returncode
        return exit_code, raw_output.decode("UTF-8")

    def hassyspath(self, _):
        return False

    def __repr__(self):
        return (
            f"UFTPMOUNTFS({self.host!r}, port={self.port!r})"
            ", base_path={self.base_path!r}, mount_dir={self.mount_dir!r}"
        )

    __str__ = __repr__


class UFTPMountOpener(Opener):
    """Defines the Opener class used to open UFTP Mount FS instances based on a URL"""

    protocols = ["uftpmount"]

    def _parse(self, resource_url):
        tok = resource_url.split("/rest/")
        auth_url = "https://" + tok[0]
        tok2 = tok[1].split(":")
        auth_url = auth_url + "/rest/" + tok2[0]
        base_dir = tok2[1] if len(tok) > 1 else "/"
        tok3 = base_dir.split("==")
        base_dir = tok3[0]
        mount_dir = tok3[1] if len(tok3) > 1 else "/uftp_mount"
        return auth_url, base_dir, mount_dir

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
        auth_url, base_dir, mount_dir = self._parse(parse_result.resource)
        cred = self._create_credential(parse_result)
        return UFTPMOUNTFS(auth_url, cred, base_dir, mount_dir)
