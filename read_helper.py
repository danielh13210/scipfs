import sys
import os
import subprocess
import redis
from datetime import datetime,timezone

this_dir=os.path.dirname(__file__)

def get_document(entity_id,redis_conn):
    # transparent cache
    entity_id=entity_id.lower()
    data=subprocess.check_output([os.path.join(this_dir,"scp-cleanfetch","target","debug","scp-cleanfetch"),entity_id],text=True)
    lines=data.splitlines()
    html='\n'.join(lines[:-1])
    creation_date=lines[-1][12:]
    creation_date=datetime.fromisoformat(creation_date)
    now=datetime.now(timezone.utc)
    is_new=(now-creation_date).total_seconds()<86400
    def flatten_page(content):
      proc=subprocess.Popen(["node",os.path.join(this_dir,"flatten.js")],stdin=subprocess.PIPE,stdout=subprocess.PIPE,text=True)
      proc.stdin.write(content)
      proc.stdin.flush()
      proc.stdin.close()
      proc.wait()
      return proc.stdout.read().strip()
    text_out=flatten_page(html)
    redis_conn.set(entity_id,text_out,ex=1200 if is_new else 3600)
    if redis_conn.get(entity_id+'.renewing') is not None:
        redis_conn.delete(entity_id+'.renewing')
    print(text_out)

redis_addr=os.environ['REDIS_URI']
redis_conn=redis.Redis.from_url(redis_addr)
get_document(sys.argv[1],redis_conn)
