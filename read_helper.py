import sys
import os
import subprocess
import redis
import time

this_dir=os.path.dirname(__file__)

def get_document(entity_id,redis_conn):
    # transparent cache
    entity_id=entity_id.lower()
    data=subprocess.check_output([os.path.join(this_dir,"scp-cleanfetch","target","debug","scp-cleanfetch"),entity_id],text=True)
    lines=data.splitlines()
    html='\n'.join(lines[:-1])
    creation_date=lines[-1][12:]
    print(creation_date)
    text_out=flatten_page(content_block)
    redis_conn.set(entity_id,text_out,ex=3600)
    if redis_conn.get(entity_id+'.renewing') is not None:
        redis_conn.delete(entity_id+'.renewing')
    print(text_out)

redis_addr=os.environ['REDIS_URI']
redis_conn=redis.Redis.from_url(redis_addr)
get_document(sys.argv[1],redis_conn)
