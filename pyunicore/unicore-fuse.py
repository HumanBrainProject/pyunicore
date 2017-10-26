#!/usr/bin/env python
from __future__ import print_function, absolute_import, division

from sys import argv, exit
from stat import S_IFDIR, S_IFLNK, S_IFREG
from os.path import basename

#from time import mktime
import time
import logging
#from dateutil.parser import parse as dateparse

import pyunicore.client as uc

from fuse import FUSE, FuseOSError, Operations, LoggingMixIn
from errno import ENOENT

class UFS(LoggingMixIn, Operations):
    '''
    A simple UNICORE REST-API filesystem (read-only for files)
    Needed: storage base URL and authentication header value (eg. an oauth token)
    '''
    
    my_uid = 1000
    my_gid = 1000

    fh = 0
    open_files = {}
    
    def __init__(self, storage_url, auth_token, oidc=False, path="."):
        self.transport = uc.Transport(auth_token, oidc=oidc)
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

    def open(self, path, flags):
        f = self.storage.stat(path).raw()
        self.fh += 1
        self.open_files[self.fh] = f
        return self.fh
        
    def read(self, path, size, offset, fh):
        f = self.open_files.get(fh, None)
        if f is None:
            f = self.storage.stat(path).raw()
        return f.read(size)

    def readdir(self, path, fh):
        ls = []
        for name in self.storage.contents(path)["content"]:
            self.log.debug(name)
            if name.endswith("/"):
                name = name[:-1]
            ls.append(basename("/"+name))
        return ['.', '..'] + ls

    def readlink(self, path):
        raise Exception("Not yet implemented")
        return self.sftp.readlink(path)

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
        raise Exception("Not yet implemented")
        f = None #...open(path, 'r+')
        f.seek(offset, 0)
        f.write(data)
        f.close()
        return len(data)


if __name__ == '__main__':
    if len(argv) < 4:
        print('usage: %s <storage_url> <mountpoint> <auth_header_value> [DEBUG]' % argv[0])
        exit(1)
    if len(argv) > 4 and argv[4]=="DEBUG":
        logging.basicConfig(level=logging.DEBUG)
    fuse = FUSE(UFS(argv[1], argv[3]), argv[2], foreground=True, nothreads=True)
