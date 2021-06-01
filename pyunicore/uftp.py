from ftplib import FTP
from pyunicore.client import Resource
import os, os.path, stat
from time import localtime, time, mktime, strftime, strptime
from sys import maxsize

'''
    Classes for interacting with a UFTP Auth server, creating a UFTP session
    and performing various data management functions
'''

class UFTP(object):
    '''
    Authenticate UFTP sessions via Authserver
    Use ftplib to open the session and interact with the UFTPD server
    '''

    uftp_session_tag = "___UFTP___MULTI___FILE___SESSION___MODE___"

    def __init__(self, transport=None, base_url=None, base_dir=""):
        self.transport = transport
        self.base_url = base_url
        if base_dir!="" and not base_dir.endswith("/"):
            base_dir += "/"
        self.base_dir = base_dir
        self.ftp = None
        self.uid = os.getuid()
        self.gid = os.getgid()

    def connect(self):
        ''' authenticate and open a UFTP session '''
        host, port, password = self.authenticate()
        self.open_uftp_session(host, port, password)

    def open_uftp_session(self, host, port, password):
        ''' open an FTP session at the given UFTP server '''
        self.ftp = FTP()
        self.ftp.connect(host,port)
        self.ftp.login("anonymous", password)

    def authenticate(self):
        ''' authenticate to the auth server and return a tuple (host, port, one-time-password) '''
        url = self.base_url
        req = {
            "persistent": "true",
            "serverPath": self.base_dir+self.uftp_session_tag
        }
        params = self.transport.post(url=url, json=req).json()
        return params['serverHost'], params['serverPort'], params['secret']

    __perms = {"r": stat.S_IRUSR, "w": stat.S_IWUSR, "x": stat.S_IXUSR}
    __type  = {"file": stat.S_IFREG, "dir": stat.S_IFDIR}

    def normalize(self, path):
        if path is not None:
            if path.startswith("/"):
                path = path[1:]
        return path

    def stat(self, path):
        ''' get os.stat() style info about a remote file/directory '''
        path = self.normalize(path)
        self.ftp.putline("MLST %s" % path)
        lines = self.ftp.getmultiline().split("\n")
        if len(lines)!=3 or not lines[0].startswith("250"):
            raise IOError("File not found. Server reply: %s " % str(lines[0]))
        try:
            infos = lines[1].strip().split(" ")[0].split(";")
            raw_info = {}
            for x in infos:
                try:
                    tok = x.split("=")
                    if len(tok)!=2:
                        continue
                    raw_info[tok[0]] = tok[1]
                except:
                    pass
            st = {}
            st['st_size'] = int(raw_info['size'])
            st['st_uid'] = self.uid
            st['st_gid'] = self.gid
            mode = UFTP.__type[raw_info.get('type', stat.S_IFREG)]
            for x in raw_info['perm']:
                mode = mode | UFTP.__perms.get(x, stat.S_IRUSR)
            st['st_mode'] = mode
            ttime = int(mktime(strptime(raw_info['modify'], "%Y%m%d%H%M%S")))
            st['st_mtime'] = ttime
            st['st_atime'] = ttime
            return st
        except Exception as e:
            raise IOError(str(e))

    def listdir(self, directory):
        ''' return a list of files in the given directory '''
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
            raise IOError("Could not rename: " % reply)
        self.ftp.voidcmd("RNTO %s" % target)

    def set_time(self, mtime, path):
        path = self.normalize(path)
        stime = strftime("%Y%m%d%H%M%S", localtime(mtime))
        reply = self.ftp.sendcmd("MFMT %s %s" % (stime, path))
        if not reply.startswith("213"):
            raise IOError("Could not set time: " % reply)

    def close(self):
        try:
            self.ftp.close()
        except:
            pass

    def get_write_socket(self, path, offset):
        path = self.normalize(path)
        reply = self.ftp.sendcmd("RANG %s %s"% (offset, maxsize))
        if not reply.startswith("350"):
            raise IOError("Error setting RANG: %s" % reply)
        return self.ftp.transfercmd("STOR %s" % path)

    def get_read_socket(self, path, offset):
        path = self.normalize(path)
        return self.ftp.transfercmd("RETR %s" % path,  rest=offset)
