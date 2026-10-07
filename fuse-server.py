#!/usr/bin/env python3
import os
import sys
import errno
from stat import S_IFDIR, S_IFREG
from time import time
from fuse import FUSE, FuseOSError, Operations
import time
import redis
import subprocess

oft={}

def get_document(entity_id,redis_conn):
    entity_id=entity_id.lower()
    cached_content=redis_conn.get(entity_id)
    if cached_content:
        ttl=redis_conn.ttl(entity_id)
        if ttl<=600:
            could_lock=redis_conn.set(entity_id+'.renewing','',nx=True,ex=30)
            if could_lock:
                subprocess.Popen(["python3","read_helper.py",entity_id],stdout=subprocess.DEVNULL)
        return cached_content.decode()
    else:
        could_lock=redis_conn.set(entity_id+'.renewing','',nx=True,ex=30)
        if could_lock:
            out=subprocess.check_output(["python3","read_helper.py",entity_id],text=True)
            return out
        else:
            while redis_conn.get(entity_id+'.renewing') is not None:
                time.sleep(0.2)
            cached_content=redis_conn.get(entity_id)
            return cached_content.decode()

def all_entities_in_series(series):
    series=str(series)
    series=series.lower()
    cached_content=redis_conn.get(f'series-{series}')
    if cached_content:
        ttl=redis_conn.ttl(f'series-{series}')
        if ttl<=600:
            could_lock=redis_conn.set(f'series-{series}.renewing','',nx=True,ex=30)
            if could_lock:
                subprocess.Popen(["python3","series_read_helper.py",series],stdout=subprocess.DEVNULL)
        return cached_content.decode('utf-8').split('\0')
    else:
        could_lock=redis_conn.set(f'series-{series}.renewing','',nx=True,ex=30)
        if could_lock:
            out=subprocess.check_output(["python3","series_read_helper.py",series],text=True)
            return out.split('\0')
        else:
            while redis_conn.get(f'series-{series}.renewing') is not None:
                time.sleep(0.2)
            cached_content=redis_conn.get(f'series-{series}.renewing')
            return cached_content.decode()

class SCPDatabaseFilesystem(Operations):
    def __init__(self,redis_conn):
        self._redis_conn=redis_conn

    def getattr(self, path, fh=None):
        if path=='/':
            return {
                'st_mode': S_IFDIR | 0o555,  # It's a directory, rwxr-xr-x permissions
                'st_nlink': 12,
                'st_size': 4096,
                'st_ctime': 0,
                'st_mtime': 0,
                'st_atime': 0
            }
        elif os.path.dirname(path)=='/':
            if (filename:=os.path.basename(path))[1:]=="XXX":
                if filename[0] not in [str(n) for n in range(0,10)]:
                    raise FuseOSError(errno.ENOENT)
                return {
                    'st_mode': S_IFDIR | 0o555,  # It's a directory, rwxr-xr-x permissions
                    'st_nlink': 2,
                    'st_size': 4096,
                    'st_ctime': 0,
                    'st_mtime': 0,
                    'st_atime': 0
                }
            else:
                raise FuseOSError(errno.ENOENT)
        elif os.path.basename(path)[:-4] in all_entities_in_series(os.path.basename(os.path.dirname(path))[0]):
            return {
                'st_mode': S_IFREG | 0o444,  # It's a file, rwxr-xr-x permissions
                'st_nlink': 1,
                'st_size': 0,
                'st_ctime': 0,
                'st_mtime': 0,
                'st_atime': 0
            }
        else:
            raise FuseOSError(errno.ENOENT)

    def readdir(self, path, _fh):
        yield '.'
        yield '..'
        if path == "/":
            for i in range(0, 10):
                yield f"{i}XXX"
        else:
            series=int(os.path.basename(path)[0])
            for entity in all_entities_in_series(series):
                yield entity+'.scp' # add extension
    def open(self, path, flags):
        from secrets import randbits
        file_name=os.path.basename(path)
        reader_id=0
        while reader_id == 0 or reader_id in oft:
          reader_id=randbits(64)
        oft[reader_id]=file_name
        return reader_id

    def read(self, _, size, offset, fh):
        return get_document(oft[fh][:-4],self._redis_conn)[offset:offset+size].encode('utf-8')

    def release(self, _, fh):
        del oft[fh]
if __name__ == '__main__':
    if len(sys.argv) != 2:
        print(f"Usage: {sys.argv[0]} <mountpoint>")
        sys.exit(1)

    mountpoint = sys.argv[1]
    redis_addr=os.environ['REDIS_URI']
    redis_conn=redis.Redis.from_url(redis_addr)
    FUSE(SCPDatabaseFilesystem(redis_conn), mountpoint, nothreads=False, foreground=True, allow_other=True, direct_io=True)
