"""Self-labeler Flask app and implementation.

https://atproto.com/specs/label
https://docs.bsky.app/docs/advanced-guides/moderation#labelers

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

import arroba.util
from cryptography.hazmat.primitives import serialization
from flask import Flask
from google.cloud import error_reporting
import google.cloud.logging
import lexrpc.flask_server
import lexrpc.server
import simple_websocket

# https://docs.bsky.app/docs/advanced-guides/moderation#global-label-values
GLOBAL_LABELS = [
    '!hide',
    '!no-unauthenticated',
    '!warn',
    'graphic-media',
    'nudity',
    'porn',
    'sexual',
]

KNOWN_LABELS = [
    'bridged-from-bridgy-fed-activitypub',
    'bridged-from-bridgy-fed-web',
]

logging_client = google.cloud.logging.Client()
logging_client.setup_logging(log_level=logging.DEBUG)
logger = logging.getLogger(__name__)

error_reporting_client = error_reporting.Client()

logger.info('Loading #atproto_label private key from privkey.atproto_label.pem')
with open('privkey.atproto_label.pem', 'rb') as f:
    privkey = serialization.load_pem_private_key(f.read(), password=None)

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

            if (msg.get('kind') != 'commit'
                    or commit.get('operation') not in ('create', 'update')):
                continue

            values = [v['val'] for v in
                      commit['record'].get('labels', {}).get('values', [])
                      if v['val'] not in GLOBAL_LABELS]
            if not values:
                continue

            labels = {
                'seq': msg['time_us'],
                'labels': [],
            }
            uri = f'at://{msg["did"]}/{commit["collection"]}/{commit["rkey"]}'
            for val in values:
                if val not in KNOWN_LABELS:
                    error_reporting_client.report(f'new label! {val} {uri} {cid}')
                label = {
                    'ver': 1,
                    'src': msg['did'],
                    'uri': uri,
                    'cid': commit['cid'],
                    'val': val,
                    'cts': datetime.now().isoformat(),
                }
                arroba.util.sign(label, privkey)
                labels['labels'].append(label)

            logger.info(f'emitting to {len(subscribers)} subscribers: {uri} {labels}')
            for sub in subscribers:
                sub.put(labels)

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
assert 'jetstream' not in [t.name for t in threading.enumerate()]
Thread(target=jetstream, name='jetstream').start()


@app.get('/liveness_check')
@app.get('/readiness_check')
def health_check():
    """App Engine Flex health checks.

    https://cloud.google.com/appengine/docs/flexible/reference/app-yaml?tab=python#updated_health_checks
    """
    return 'OK'
