import os
import stat
from ftplib import FTP
from sys import maxsize
from time import localtime
from time import mktime
from time import strftime
from time import strptime

from pyunicore.client import Transport
from pyunicore.credentials import Credential


class UFTP:
    """
    Authenticate UFTP sessions via Authserver
    Uses ftplib to open the session and interact with the UFTPD server
    """

    uftp_session_tag = "___UFTP___MULTI___FILE___SESSION___MODE___"

    def __init__(self):
        self.ftp = None
        self.uid = os.getuid()
        self.gid = os.getgid()

    def connect(self, security, base_url, base_dir=""):
        """authenticate and open a UFTP session"""
        host, port, password = self.authenticate(security, base_url, base_dir)
        self.open_uftp_session(host, port, password)

    def open_uftp_session(self, host, port, password):
        """open an FTP session at the given UFTP server"""
        self.ftp = FTP()
        self.ftp.connect(host, port)
        self.ftp.login("anonymous", password)

    def authenticate(self, security, base_url, base_dir=""):
        """authenticate to the auth server and return a tuple (host, port, one-time-password)"""
        if isinstance(security, Credential):
            transport = Transport(security)
        elif isinstance(security, Transport):
            transport = security._clone()
        else:
            raise TypeError("Need Credential or Transport object")
        if base_dir != "" and not base_dir.endswith("/"):
            base_dir += "/"
        req = {
            "persistent": "true",
            "serverPath": base_dir + self.uftp_session_tag,
        }
        params = transport.post(url=base_url, json=req).json()
        return params["serverHost"], params["serverPort"], params["secret"]

    __perms = {"r": stat.S_IRUSR, "w": stat.S_IWUSR, "x": stat.S_IXUSR}
    __type = {"file": stat.S_IFREG, "dir": stat.S_IFDIR}

    def normalize(self, path):
        if path is not None:
            if path.startswith("/"):
                path = path[1:]
        return path

    def stat(self, path):
        """get os.stat() style info about a remote file/directory"""
        path = self.normalize(path)
        self.ftp.putline("MLST %s" % path)
        lines = self.ftp.getmultiline().split("\n")
        if len(lines) != 3 or not lines[0].startswith("250"):
            raise OSError("File not found. Server reply: %s " % str(lines[0]))
        infos = lines[1].strip().split(" ")[0].split(";")
        raw_info = {}
        for x in infos:
            tok = x.split("=")
            if len(tok) != 2:
                continue
            raw_info[tok[0]] = tok[1]
        st = {}
        st["st_size"] = int(raw_info["size"])
        st["st_uid"] = self.uid
        st["st_gid"] = self.gid
        mode = UFTP.__type[raw_info.get("type", stat.S_IFREG)]
        for x in raw_info["perm"]:
            mode = mode | UFTP.__perms.get(x, stat.S_IRUSR)
        st["st_mode"] = mode
        if raw_info.get("UNIX.mode", None) is not None:
            st["st_mode"] = int(raw_info["UNIX.mode"], 8)
        ttime = int(mktime(strptime(raw_info["modify"], "%Y%m%d%H%M%S")))
        st["st_mtime"] = ttime
        st["st_atime"] = ttime
        return st

    def listdir(self, directory):
        """return a list of files in the given directory"""
        listing = []
        directory = self.normalize(directory)
        self.ftp.retrlines(cmd="LIST %s" % directory, callback=listing.append)
        return [x.split(" ")[-1] for x in listing]

    def mkdir(self, directory, mode):
        directory = self.normalize(directory)
        self.ftp.voidcmd("MKD %s" % directory)

    def rmdir(self, directory):
        directory = self.normalize(directory)
        self.ftp.voidcmd("RMD %s" % directory)

    def rm(self, path):
        path = self.normalize(path)
        self.ftp.voidcmd("DELE %s" % path)

    def rename(self, source, target):
        source = self.normalize(source)
        target = self.normalize(target)
        reply = self.ftp.sendcmd("RNFR %s" % source)
        if not reply.startswith("350"):
            raise OSError("Could not rename: " % reply)
        self.ftp.voidcmd("RNTO %s" % target)

    def set_time(self, path, mtime):
        path = self.normalize(path)
        stime = strftime("%Y%m%d%H%M%S", localtime(mtime))
        reply = self.ftp.sendcmd(f"MFMT {stime} {path}")
        if not reply.startswith("213"):
            raise OSError("Could not set time: " % reply)

    def chmod(self, path, mode):
        path = self.normalize(path)
        reply = self.ftp.sendcmd(f"MFF UNIX.mode={oct(mode)[2:]}; {path}")
        if not reply.startswith("213"):
            raise OSError("Could not chmod: " % reply)

    def close(self):
        if self.ftp is not None:
            self.ftp.close()

    def _send_range(self, offset, length, rfc=False):
        end_byte = offset + length - 1 if rfc else offset + length
        self.ftp.sendcmd(f"RANG {offset} {end_byte}")

    def get_write_socket(self, path, offset):
        path = self.normalize(path)
        if offset > 0:
            self._send_range(offset, maxsize)
        else:
            self.ftp.sendcmd(f"ALLO {maxsize}")
        return self.ftp.transfercmd("STOR %s" % path)

    def get_read_socket(self, path, offset):
        path = self.normalize(path)
        return self.ftp.transfercmd("RETR %s" % path, rest=offset)
