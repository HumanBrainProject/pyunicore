#!/usr/bin/env python3
import time
import datetime
import argparse
import os
import sys
import stat
import tempfile
import errno
from getpass import getpass
from ftplib import FTP
from fusepy import FUSE, FuseOSError, Operations  # fusepy

import pyunicore.client as unicore_client
import json
import random as r

DEFAULT_DATE = '19700101000000'


def convert_time(src):
    parsed = datetime.datetime.strptime(src, '%Y%m%d%H%M%S')
    return time.mktime(parsed.timetuple())


def convert_perm(src):
    ret = 0
    if 'a' in src:
        # file, can be appended to
        ret |= stat.S_IFREG
    if 'c' in src:
        # directory
        ret |= stat.S_IFDIR
    if 'd' in src:
        # anything, can be deleted
        pass
    if 'e' in src:
        # directory, can be traversed into
        ret |= stat.S_IFDIR | 0o111
    if 'f' in src:
        # anything, can be renamed
        pass
    if 'l' in src:
        # directory, can be listed
        ret |= stat.S_IFDIR | 0o444
    if 'm' in src:
        # directory, can create new directories inside
        ret |= stat.S_IFDIR | 0o200
    if 'p' in src:
        # directory, can remove directories inside
        ret |= stat.S_IFDIR | 0o200
    if 'r' in src:
        # file, can be read
        ret |= stat.S_IFREG | 0o444
    if 'w' in src:
        # file, can be written to
        ret |= stat.S_IFREG | 0o200
    return ret


class FTPFS(Operations):
    def __init__(self, ftp):
        self._ftp = ftp
        self._dir_cache = {}
        self._file_cache = {}
        self._file_handles = {}

    def getattr(self, path, fh=None):
        try:
            file_info = self._file_cache[path]
        except KeyError:
            list(self.readdir(os.path.dirname(path), None))
            try:
                file_info = self._file_cache[path]
            except KeyError:
                raise FuseOSError(errno.ENOENT)

        perm = 0
        if 'type' in file_info:
            if file_info['type'] in {'cdir', 'dir'}:
                perm |= stat.S_IFDIR
            elif file_info['type'] == 'file':
                perm |= stat.S_IFREG
        elif 'perm' in file_info:
            perm = convert_perm(file_info['perm'])
        if 'unix.mode' in file_info:
            perm &= ~0o777
            perm |= int(file_info['unix.mode'], 8)

        ret = {
            'st_atime': int(
                convert_time(file_info.get('modify', DEFAULT_DATE))),
            'st_mtime': int(
                convert_time(file_info.get('modify', DEFAULT_DATE))),
            'st_ctime': int(
                convert_time(
                    file_info.get(
                        'create',
                        file_info.get('modify', DEFAULT_DATE)))),
            'st_gid': int(file_info.get('unix.group', '0')),
            'st_uid': int(file_info.get('unix.owner', '0')),
            'st_mode': perm,
            'st_size': int(file_info.get('size', 0)),
            'st_nlink': 0,
        }
        return ret

    def readdir(self, path, fh):
        self._ftp.cwd(path)
        if path not in self._dir_cache:
            self._dir_cache[path] = list(self._ftp.mlsd())
            for item, data in self._dir_cache[path]:
                if item == '..':
                    continue
                if item == '.':
                    item_path = path
                else:
                    item_path = os.path.join(path, item)
                self._file_cache[item_path] = data

        for item, data in self._dir_cache[path]:
            yield item

    def chmod(self, path, mode):
        raise Exception("Not yet implemented")

    def chown(self, path, uid, gid):
        raise Exception("Not yet implemented")

    def readlink(self, path):
        raise FuseOSError(errno.ENOSYS)

    def symlink(self, name, target):
        raise Exception("Not yet implemented")

    def mknod(self, path, mode, dev):
        raise Exception("Not yet implemented")

    def mkdir(self, path, mode):
        raise Exception("Not yet implemented")

    def rmdir(self, path):
        raise Exception("Not yet implemented")

    def statfs(self, path):
        raise FuseOSError(errno.ENOSYS)

    def unlink(self, path):
        raise Exception("Not yet implemented")

    def rename(self, old, new):
        raise Exception("Not yet implemented")

    def utimens(self, path, times=None):
        raise FuseOSError(errno.ENOSYS)

    def open(self, path, flags):
        handle = tempfile.SpooledTemporaryFile()
        self._file_handles[self._path_to_fd(path)] = handle
        self._ftp.retrbinary('RETR ' + path, handle.write)
        return self._path_to_fd(path)

    def create(self, path, mode, fi=None):
        raise Exception("Not yet implemented")

    def read(self, path, length, offset, fh):
        self._file_handles[self._path_to_fd(path)].seek(offset)
        return self._file_handles[self._path_to_fd(path)].read(length)

    def write(self, path, buf, offset, fh):
        raise Exception("Not yet implemented")

    def truncate(self, path, length, fh=None):
        raise Exception("Not yet implemented")

    def flush(self, path, fh):
        raise Exception("Not yet implemented")

    def release(self, path, fh):
        raise Exception("Not yet implemented")

    def fsync(self, path, fdatasync, fh):
        return self.flush(path, fh)

    def _path_to_fd(self, path):
        return hash(path)

    def _wipe_cache(self):
        self._dir_cache = {}
        self._file_cache = {}

# function for one-time-password generation
def otpgen():
    otp=""
    for i in range(16):
        otp+=str(r.randint(1,9))
    return otp

def connect(storage):
    
    # create a UFTP session
    otp = otpgen()
    req = {"protocol": "UFTP",
           "file": unicore_client.UFTP.uftp_session_tag,
           "extraParameters": {"uftp.secret": otp, }
    }
    storage_url = storage.resource_url
    
    export_url = storage_url + "/exports"
    tr = storage.transport
    res = tr.post(url=export_url, json=req)
    print (json.dumps(res.json(), indent=2))

    # we will use this UFTP server host/port
    # TODO get from reply
    uftp_host = "localhost"
    uftp_port = 64434

    # connect to the UFTP server
    ftp = FTP()
    ftp.connect(uftp_host,uftp_port)
    ftp.login("anonymous", otp)
    ftp.putcmd("SYST")
    ftp.putcmd("FEAT")
    while not ftp.getline().startswith("211 E"):
        pass
    print("Session established")
    return ftp

def main():
    from base64 import b64encode
    
    token = b64encode(b"demouser:test123").decode("ascii")
    tr = unicore_client.Transport(token, oidc=False)
    # storage_url = "https://fzj-unic.fz-juelich.de:7112/FZJ_JURECA/rest/core/storages/SCRATCH"
    storage_url = "https://localhost:8080/VENUS/rest/core/storages/projects"
    
    storage = unicore_client.Storage(tr,storage_url)
    ftp = connect(storage)

    if not args.daemon:
        print('Connected')

    dest = "/tmp/mount"
    
    FUSE(FTPFS(ftp), dest, nothreads=True, foreground=True)


if __name__ == '__main__':
    main()
