import sys
import os
import requests
import redis
from lxml import html

this_dir=os.path.dirname(__file__)

def get_entities_in_series(series,redis_conn):
    # transparent cache
    series=int(series.lower())
    resp=requests.get(f'https://scp-wiki.wikidot.com/scp-series-{series+1}') # indexing on wikidot starts from 1
    d=html.document_fromstring(resp.text)
    series_list=d.xpath('//div[@id="page-content"]/div[contains(@class,"content-panel")]/ul/li/a/text()')
    series_list_ser='\0'.join(series_list)
    redis_conn.set(f'series-{series}',series_list_ser.encode('utf-8'),ex=3600)
    if redis_conn.get(f'series-{series}.renewing') is not None:
        redis_conn.delete(f'series-{series}.renewing')
    print(series_list_ser,end="")

redis_addr=os.environ['REDIS_URI']
redis_conn=redis.Redis.from_url(redis_addr)
get_entities_in_series(sys.argv[1],redis_conn)
