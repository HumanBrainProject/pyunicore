#!/usr/bin/env python3

from errno import EIO, ENOENT, ENOSYS, EROFS
from fuse import FUSE, FuseOSError, Operations
import os
from time import time
from pyunicore.client import Transport
from pyunicore.uftp import UFTP

class UFTPFile(object):
    ''' handle to an in-progress read or write transfer '''
    
    BUFFER_SIZE = 65536    
    
    def __init__(self, path, uftp_session: UFTP):
        self.uftp_session = uftp_session;
        self.path = path
        self.pos = 0
        self.data = None
        self.write_mode = False

    def close(self):
        self.close_data()

    def close_data(self):
        if self.data is not None:
            try:
                self.data.close()
            except:
                pass
        self.data = None
        self.pos = 0

    def open_data(self, position, write_mode = False):
        ''' open data channel before a sequence of read/write operations '''
        self.write_mode = write_mode
        if self.write_mode:
            _sock = self.uftp_session.get_write_socket(self.path, position)
        else:
            _sock = self.uftp_session.get_read_socket(self.path, position)
        self.pos = position
        if self.write_mode:
            self.data = _sock.makefile("wb", buffering = UFTPFile.BUFFER_SIZE)
        else:
            self.data = _sock.makefile("rb", buffering = UFTPFile.BUFFER_SIZE)

    def read(self, offset, size):
        if self.data is not None and self.write_mode:
            raise IOError("Not open for reading")
        if self.data is None:
            self.open_data(offset, write_mode = False)
        data_block = self.data.read(size)
        self.pos+=len(data_block)
        return data_block
    
    def write(self, offset, data):
        if self.data is not None and not self.write_mode:
            raise IOError("Not open for writing")
        if self.data is None:
            self.open_data(offset, write_mode = True)
        to_write = len(data)
        write_offset = 0
        while to_write > 0:
            written = self.data.write(data[write_offset:])
            if written is None:
                written = 0
            write_offset += written
            to_write -= written
        self.data.flush()
        self.pos+=len(data)
        return len(data)

class UFTPDriver(Operations):
    '''
    FUSE Driver
    Connects to uftpd at host:port with
    the given session password (which can be obtained by
    authenticating to an Authserver or UNICORE/X)
    '''

    def __init__(self, host, port, password, debug=False):
        self.host = host
        self.port = port
        self.password = password
        self.uftp_session = self.new_session()
        self.last_file = None
        self.file_map = {}
        self.next_file_handle = 0;
        self.debug = debug

    def new_session(self):
        uftp_session = UFTP()
        uftp_session.open_uftp_session(self.host, self.port, self.password)
        return uftp_session

    def chmod(self, path, mode):
        raise FuseOSError(ENOSYS)
        
    def chown(self, path, uid, gid):
        raise FuseOSError(ENOSYS)
        
    def create(self, path, mode):
        if self.debug:
            print("create %s %s" % (path, mode))
        fh = self.open(path, os.O_WRONLY)
        f = self.file_map[fh]
        f.write(0, [])
        # TBD f.chmod(mode)
        return fh

    def destroy(self, path):
        for f in self.file_map.values():
            try:
                f.close()
            except:
                pass
        self.uftp_session.close()

    def getattr(self, path, fh=None):
        try:
            return self.uftp_session.stat(path)
        except IOError:
            raise FuseOSError(ENOENT)

    def mkdir(self, path, mode):
        return self.uftp_session.mkdir(path, mode)

    def open(self, path, fi_flags):
        fh = self.next_file_handle;
        if os.O_RDWR & fi_flags:
            raise FuseOSError(EIO)
        if self.debug:
            print("open [%s] %s flags=%s" % (fh, path, fi_flags))
        self.next_file_handle+=1
        f = UFTPFile(path, self.new_session())
        self.file_map[fh] = f
        return fh
    
    def read(self, path, size, offset, fh):
        if self.debug:
            print("read [%s] %s len=%s offset=%s" % (fh, path,size,offset))
        f = self.file_map[fh]
        return f.read(offset, size)

    def readdir(self, path, fh):
        return ['.', '..'] + [name for name in self.uftp_session.listdir(path)]

    def readlink(self, path):
        raise FuseOSError(ENOSYS)

    def rename(self, old, new):
        return self.uftp_session.rename(old, new)

    def release(self, path, fh):
        if self.debug:
            print("release [%s] %s" % (fh, path))
        f = self.file_map[fh]
        f.close()
        self.file_map.__delitem__(fh)

    def rmdir(self, path):
        return self.uftp_session.rmdir(path)

    def symlink(self, target, source):
        raise FuseOSError(ENOSYS)
        
    def truncate(self, path, length, fh=None):
        if self.debug:
            print("truncate %s" % path)
        pass
        
    def unlink(self, path):
        return self.uftp_session.rm(path)

    def utimens(self, path, times=None):
        if times is None:
            _time = time()
        else:
            _time = times[0]
        self.uftp_session.set_time(_time, path)

    def write(self, path, data, offset, fh):
        if self.debug:
            print("write [%s] %s len=%s offset=%s" % (fh, path, len(data), offset))
        f = self.file_map[fh]
        f.write(offset, data)
        return len(data)


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('-d', '--debug', action='store_true', help="debug mode (also keeps process in the foreground)")
    parser.add_argument('-P', '--password', help = "one-time password (if not given, it is expected in the environment UFTP_PASSWORD)")
    parser.add_argument('address', help = "UFTPD server's address (host:port)")
    parser.add_argument('mount_point', help = "the local mount directory (must exist and be empty)")
    
    args = parser.parse_args()
    _debug = args.debug
    _pwd = args.password
    if _pwd is None:
        _pwd = os.getenv("UFTP_PASSWORD")
    if _pwd is None:
        raise Exception("UFTP one-time password must be given with '-P ...' or as environment UFTP_PASSWORD")
    _host, _port = args.address.split(":")
 
    fuse = FUSE(
        UFTPDriver(_host, int(_port), _pwd),
        args.mount_point,
        debug = args.debug,
        foreground = args.debug,
        nothreads = True,
        big_writes = True, 
        max_read = 131072, 
        max_write = 131072
        )
