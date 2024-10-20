"""Flask config and env vars.

https://flask.palletsprojects.com/en/latest/config/
"""
import logging
import os

if False:
    ENV = 'development'
    SECRET_KEY = 'sooper seekret'
else:
    ENV = 'production'
    with open('flask_secret_key') as f:
        SECRET_KEY = f.read().strip()

    logging.getLogger().setLevel(logging.INFO)
    # if logging_client := getattr(appengine_config, 'logging_client'):
    #     logging_client.setup_logging(log_level=logging.INFO)

    for logger in ('lexrpc',):
        logging.getLogger(logger).setLevel(logging.DEBUG)

os.environ.setdefault('APPVIEW_HOST', 'api.bsky.local')
os.environ.setdefault('RELAY_HOST', 'bsky.network.local')
os.environ.setdefault('PLC_HOST', 'plc.bsky.local')
os.environ.setdefault('JETSTREAM_HOST', 'jetstream.local')
