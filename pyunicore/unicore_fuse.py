#!/usr/bin/env python
from __future__ import print_function, absolute_import, division

from sys import argv, exit
from stat import S_IFDIR, S_IFLNK, S_IFREG
from os import getgid,getuid
from os.path import basename

import time
import logging
#from dateutil.parser import parse as dateparse

import pyunicore.client as uc

from fuse import FUSE, FuseOSError, Operations, LoggingMixIn
from errno import ENOENT

class FileHandle():
    ''' Helper to minimize REST calls '''

    position = 0
    conn = None
    ufile = None

    def __init__(self, ufile, offset, size):
        self.ufile = ufile
        self._open(offset, size)

    def _open(self, offset, size):
        self.conn = self.ufile.raw(offset, size)
        self.position = offset

    def close(self):
        if self.conn is not None:
            try:
                self.conn.close()
            except:
                pass

    def read(self, offset, size):
        if self.conn is None or self.conn.closed:
            self._open(offset, size)
        elif offset!=self.position:
            self.close()
            self._open(offset, size)

        if size>=0:
            x = self.conn.read(size)
        else:
            x = self.conn.read()

        self.position += len(x)
        return x

class UFS(LoggingMixIn, Operations):
    '''
    A simple UNICORE REST-API filesystem (read-only for files)
    Needed: storage base URL and authentication header value (eg. an oauth token)
    '''

    my_uid = getuid()
    my_gid = getgid()

    fh = 0
    open_files = {}
    
    def __init__(self, transport, storage_url, path="."):
        self.transport = transport
        self.storage = uc.Storage(self.transport, storage_url)
        self.root = path

    def chmod(self, path, mode):
        raise Exception("Not yet implemented")

    def chown(self, path, uid, gid):
        raise Exception("Not yet implemented")

    def create(self, path, mode):
        raise Exception("Not yet implemented")
        f.chmod(mode)
        f.close()
        return 0

    def getattr(self, path, fh=None):
        try:
            st = self.storage.stat(path).properties
        except:
            raise FuseOSError(ENOENT)

        ret = {}
        if(st['isDirectory']):
           ret['st_mode'] = (S_IFDIR | 0o700)
        else:
           ret['st_mode'] = (S_IFREG | 0o700)
        ret['st_uid'] = self.my_uid
        ret['st_gid'] = self.my_gid
        ret['st_size'] = long(st['size'])
        ret['st_atime'] = long(time.time())
        times = st['lastAccessed']
        #ret['st_mtime'] = long(mktime(dateparse(times).timetuple()))
        ret['st_mtime'] = long(time.time())
        return ret

    def mkdir(self, path, mode):
        self.storage.mkdir(path)

    def _open(self, path, size, offset):
        pf = self.storage.stat(path)
        return FileHandle(pf, offset, size)

    def open(self, path, flags):
        f = self._open(path, -1, 0)
        self.fh += 1
        self.open_files[self.fh] = f
        return self.fh

    def release(self, path, fh):
        x = self.open_files[self.fh]
        if x is not None:
            x.close()
        self.open_files[self.fh] = None
        
    def read(self, path, size, offset, fh):
        f = self.open_files.get(fh, None)
        return f.read(offset, size)

    def readdir(self, path, fh):
        ls = []
        for name in self.storage.contents(path)["content"]:
            if name.endswith("/"):
                name = name[:-1]
            ls.append(basename("/"+name))
        return ['.', '..'] + ls

    def readlink(self, path):
        raise Exception("Not yet implemented")

    def rename(self, old, new):
        self.storage.rename(old, self.root + new)

    def rmdir(self, path):
        self.storage.rmdir(self.root + path)

    def symlink(self, target, source):
        raise Exception("Not implemented.")

    def truncate(self, path, length, fh=None):
        raise Exception("Not yet implemented")    

    def unlink(self, path):
        return self.storage.remove(path)

    def utimens(self, path, times=None):
        raise Exception("Not yet implemented")

    def write(self, path, data, offset, fh):
        raise Exception("Not implemented")


if __name__ == '__main__':
    if len(argv) < 4:
        print('usage: %s <storage_url> <mountpoint> <oauth_access_token> [DEBUG]' % argv[0])
        exit(1)
    if len(argv) > 4 and argv[4]=="DEBUG":
        logging.basicConfig(level=logging.DEBUG)
    transport = uc.Transport(argv[3], oidc=True)
    fuse = FUSE(UFS(transport, argv[1]), argv[2], foreground=True, nothreads=True)
