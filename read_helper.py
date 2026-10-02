import sys
import os
from playwright.sync_api import sync_playwright
import redis
import time

jsfile=open('flatten.js','r')
parser_code=jsfile.read()
jsfile.close()
pw_pause=os.environ.get("PW_PAUSE")=="1"
pw_display=os.environ.get("PW_DISPLAY")=="1"

def get_document(entity_id,pw_context,redis_conn):
    # transparent cache
    entity_id=entity_id.lower()
    page=pw_context.pages[0]
    page.goto(f'https://scp-wiki.wikidot.com/{entity_id}')
    content_block=page.locator('//div[@id="page-content"]')
    def flatten_page(content_block):
        return content_block.evaluate(parser_code)
    text_out=flatten_page(content_block)
    if pw_pause:
        while 1:time.sleep(9999)
    page.close()
    redis_conn.set(entity_id,text_out,ex=3600)
    print(text_out)

redis_addr=os.environ['REDIS_URI']
redis_conn=redis.Redis.from_url(redis_addr)
with sync_playwright() as p:
    browser = p.firefox.launch(headless=not pw_display)
    context=browser.new_context()
    context.new_page()
    time.sleep(0.6)
    get_document(sys.argv[1],context,redis_conn)
