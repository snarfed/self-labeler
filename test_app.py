"""Unit tests for app.py."""
from threading import Thread
from unittest import TestCase

from lexrpc.tests.test-client import FakeWebsocketClient

from app import app, jetstream



class AppTest(TestCase):
    def setUp(self):
        simple_websocket.Client = FakeWebsocketClient
        FakeWebsocketClient.sent = []
        FakeWebsocketClient.to_receive = []

    def test_label(self):
        FakeWebsocketClient.to_receive = []
        Thread(target=jetstream, daemon=True).start()
