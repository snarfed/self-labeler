"""Self-labeler Flask app and implementation.

Uses jetstream:
https://github.com/bluesky-social/jetstream

Example command line:
websocat 'wss://jetstream2.us-east.bsky.network/subscribe?wantedCollections=app.bsky.feed.post'
"""
from datetime import datetime
import json
import logging
import os
from pathlib import Path
from queue import Queue
import threading
from threading import Lock, Thread

from flask import Flask
import lexrpc.flask_server
import lexrpc.server
import simple_websocket

logger = logging.getLogger(__name__)
logging.basicConfig()

# elements are Queues of lists of dict com.atproto.label.defs objects to emit
subscribers = []
subscribers_lock = Lock()


# Flask app
app = Flask(__name__)
app.json.compact = False
app_dir = Path(__file__).parent
app.config.from_pyfile(app_dir / 'config.py')


# ATProto XRPC server
xrpc_server = lexrpc.server.Server(validate=True)
lexrpc.flask_server.init_flask(xrpc_server, app)


def jetstream():
    host = os.environ['JETSTREAM_HOST']
    logger.info(f'connecting to jetstream at {host}')

    ws = simple_websocket.Client(f'wss://{host}/subscribe?wantedCollections=app.bsky.feed.post&wantedCollections=app.bsky.actor.profile')
    while True:
        try:
            msg = json.loads(ws.receive())
            commit = msg.get('commit')
            if (msg.get('kind') == 'commit'
                    and commit.get('operation') in ('create', 'update')):
                uri = f'at://{msg["did"]}/{commit["collection"]}/{commit["rkey"]}'
                labels = [{
                    'ver': 1,
                    'src': msg['did'],
                    'uri': uri,
                    'cid': commit['cid'],
                    'val': label['val'],
                    'cts': datetime.now().isoformat(),
                    # 'sig': , TODO
                } for label in commit['record'].get('labels', {}).get('values', [])]
                if labels:
                    logger.info(f'emitting to {len(subscribers)} subscribers: {uri} {[l["val"] for l in labels]}')
                    for sub in subscribers:
                        sub.put({
                            'seq': msg['time_us'],
                            'labels': labels,
                        })

        except simple_websocket.ConnectionClosed as cc:
            logger.info(f'reconnecting after jetstream disconnect: {cc}')


@xrpc_server.method('com.atproto.label.subscribeLabels')
def subscribe_labels(cursor=None):
    if cursor:
        logger.info(f'ignoring cursor {cursor}, starting at head')
        # raise NotImplementedError('cursor not yet supported')

    labels = Queue()
    with subscribers_lock:
        subscribers.append(label)

    try:
        while True:
            yield labels.get()
    finally:
        subscribers.remove(labels)


# start jetstream consumer
# if LOCAL_SERVER or not DEBUG:
assert 'jetstream' not in [t.name for t in threading.enumerate()]
Thread(target=jetstream, name='jetstream').start()


@app.get('/liveness_check')
@app.get('/readiness_check')
def health_check():
    """App Engine Flex health checks.

    https://cloud.google.com/appengine/docs/flexible/reference/app-yaml?tab=python#updated_health_checks
    """
    return 'OK'
