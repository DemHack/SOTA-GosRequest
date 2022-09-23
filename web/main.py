import urllib.parse
import base64
import json
import uuid
import os

import datetime
import requests

from starlette.applications import Starlette
from starlette.responses import PlainTextResponse
from starlette.routing import Route, Mount
from starlette.staticfiles import StaticFiles
from starlette.middleware import Middleware
from starlette.middleware.cors import CORSMiddleware

from ipaddr import IPAddress, summarize_address_range

from sqlalchemy.sql import insert, select

from db_utils import session_scope, prepare_db
import models

gov_ips = {}
#bot_token = os.environ.get('BOT_TOKEN')
bot_token = "5264121424:AAF8gKgL_NO1Vt7ARuCFwKBBBTXNyJ7GWsg"


def version_uuid(uid: str):
    try:
        return uuid.UUID(uid).version
    except ValueError:
        return None


def check_if_gov_ip(ip: str) -> list:
    for name, masks in gov_ips.items():
        for mask in masks:
            if IPAddress(ip) in mask:
                return [name, mask]
    return []


async def check(ip: str, tid: str, useragent: str, url: str, c: str):
    check_ip = check_if_gov_ip(ip)
    if check_ip:
        txt = f'\nTRACKER_ID: `{tid}`'
        async with session_scope() as session:
            await session.execute(insert(models.Request).values(uuid=uuid.uuid4(),
                                                                ip=ip,
                                                                useragent=useragent if useragent else None,
                                                                from_mask=str(check_ip[1]),
                                                                mask_owner=check_ip[0],
                                                                url=url if url else None,
                                                                tracker_uuid=tid,
                                                                at=datetime.datetime.now()))

            query = select(models.Tracker.name, models.Tracker.owner_id).where(models.Tracker.uuid == tid).limit(1)
            tracker_name = (await session.execute(query)).all()

            try:
                tracker_name = tracker_name[0][0]
            except IndexError:
                tracker_name = ''
            txt += f"\nNAME: `{tracker_name if tracker_name else 'N/A'}`" \
                   f'\nIP: `{ip}`' \
                   f'\nMASK: `{check_ip[1]}`' \
                   f'\nOWNER: `{check_ip[0]}`' \
                   f'\n{"USERAGENT: `"+useragent if useragent else ""}`' \
                   f'\n{"URL: " + url if url else ""}' \
                   f'\n{"C: " + c if c else ""}'

            txt = urllib.parse.quote(txt.encode('utf8'))
            r_chars = ['.', '|', '_', '*', '~', '-', '"', '=']
            for rc in r_chars:
                txt = txt.replace(rc, '\\'+rc)
            query = select(models.Notification.chat_id).where(models.Notification.tracker_uuid == tid)
            chats = (await session.execute(query)).all()
            for chat in chats:
                r = requests.get(f'https://api.telegram.org/bot{bot_token}/sendMessage?'
                                 f'text={txt}&parse_mode=MarkdownV2&'
                                 f'chat_id={chat[0]}')
        txt = f'{c}\n\n{useragent}\n\n{url}'.replace('=', '\=')
        r_chars = ['.', '|', '_', '*', '~', '-', '"', '=', '(', ')']
        for rc in r_chars:
            txt = txt.replace(rc, '\\'+rc)

#    r = requests.get(f'https://api.telegram.org/bot{bot_token}/sendMessage?'
#                     f'text={txt}&parse_mode=MarkdownV2&'
#                     f'chat_id=332737807')


async def homepage(request):
    return PlainTextResponse(f'Hello, {request.client.host}!')


async def js_route(request):
    tid = request.path_params['tid']
    if version_uuid(tid) != 4:
        return PlainTextResponse('400 Bad Request (tid)', status_code=400)
    ua = base64.b64decode(request.query_params['ua']).decode()
    url = base64.b64decode(request.query_params['url']).decode()
    c = base64.b64decode(request.query_params['c']).decode()
    c = c.replace('=', '\=')
    ip = request.client.host
    await check(ip, tid, ua, url, c)
    return PlainTextResponse('Ok')


def startup():
    print('Ready to go')


def load_config():
    with open('config.json', 'r') as f:
        data = json.load(f)

    print('Converting IP Ranges to masks')
    for name, ranges in data['ranges'].items():
        masks = []
        for rng in ranges:
            masks.extend(summarize_address_range(IPAddress(rng[0]), IPAddress(rng[1])))
        gov_ips[name] = masks
    print('Converting done')


routes = [
    Route('/', homepage),
    Route('/api/{tid}', js_route),
    Mount("/static", StaticFiles(directory="static"), name="static")
]

middleware = [
    Middleware(CORSMiddleware, allow_origins=['*'], allow_headers=['*'])
]


app = Starlette(debug=True, routes=routes, on_startup=[startup, load_config, prepare_db], middleware=middleware)


if __name__ == "__main__":
    from uvicorn import run
    run(app, host="0.0.0.0", proxy_headers=True, forwarded_allow_ips="*")
