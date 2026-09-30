#!/usr/bin/env python3
import os
import sys
import errno
from stat import S_IFDIR, S_IFREG
from time import time
from fuse import FUSE, FuseOSError, Operations
import requests
from lxml import html
from playwright.sync_api import sync_playwright
import redis

oft={}

def get_document(entity_id,pw_context,redis_conn):
    # transparent cache
    entity_id=entity_id.lower()
    cached_content=redis_conn.get(entity_id)
    ttl=redis_conn.ttl(entity_id)
    if cached_content is not None and ttl>=600: return cached_content.decode()
    page=pw_context.new_page()
    page.goto(f'https://scp-wiki.wikidot.com/{entity_id}')
    content_block=page.locator('//div[@id="page-content"]')
    def flatten_page(content_block):
        objects=content_block.locator("> p, > blockquote")
        text_blocks=[]
        for object in objects.all():
            if object.evaluate("el => el.tagName").lower()=="blockquote":
                content="```\n"+flatten_page(object)+"\n```"
            else: # it must be a p
                content=''.join(object.all_inner_texts())
            text_blocks.append(content)
        return '\n\n'.join(text_blocks)
    text_out=flatten_page(content_block)
    page.close()
    redis_conn.set(entity_id,text_out,ex=3600)
    return text_out


def all_entities_in_series(series):
    resp=requests.get(f'https://scp-wiki.wikidot.com/scp-series-{series+1}') # indexing on wikidot starts from 1
    d=html.document_fromstring(resp.text)
    return d.xpath('//div[@id="page-content"]/div[contains(@class,"content-panel")]/ul/li/a/text()')

class SCPDatabaseFilesystem(Operations):
    def __init__(self,pw_context,redis_conn):
        self._pw_context=pw_context
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
        elif os.path.dirname(path)=='/' and (filename:=os.path.basename(path))[1:]=="XXX":
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
        elif ((len(entity_id:=(filename:=os.path.basename(path))[4:-4])==4 and entity_id[0]==os.path.basename(os.path.dirname(path))[0]) or (len(entity_id)==3 and os.path.basename(os.path.dirname(path))[0]=='0')) and filename[:4]=="SCP-" and filename[-4:]==".scp":
            return {
                'st_mode': S_IFREG | 0o444,  # It's a file, rwxr-xr-x permissions
                'st_nlink': 1,
                'st_size': len(get_document('SCP-'+entity_id,self._pw_context,self._redis_conn)),
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
        return get_document(oft[fh][:-4],self._pw_context,self._redis_conn)[offset:offset+size].encode('utf-8')

    def release(self, _, fh):
        del oft[fh]
if __name__ == '__main__':
    if len(sys.argv) != 2:
        print(f"Usage: {sys.argv[0]} <mountpoint>")
        sys.exit(1)

    mountpoint = sys.argv[1]
    redis_addr=os.environ['REDIS_URI']
    redis_conn=redis.Redis.from_url(redis_addr)
    with sync_playwright() as p:
        context = p.firefox.launch_persistent_context(headless=True,user_data_dir="cache")
        FUSE(SCPDatabaseFilesystem(context, redis_conn), mountpoint, nothreads=True, foreground=True, allow_other=True)
