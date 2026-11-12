"""Real C++ process + TCP/UDP integration tests, no simulated server."""
from collections import deque
import hashlib
import json
from pathlib import Path
import socket
import struct
import tempfile
import threading
import time
import unittest

from lan_chat.client import ChatClient
from lan_chat.native_server import NativeServer
from lan_chat.protocol import (MAX_FRAME, ProtocolError, canonical, decode, encode,
                               make_packet, recv_frame, send_frame)


class Inbox:
    def __init__(self):
        self.events = deque()
        self.condition = threading.Condition()

    def put(self, event, body):
        with self.condition:
            self.events.append((event, body))
            self.condition.notify_all()

    def wait(self, event, check=lambda body: True, timeout=5):
        deadline = time.monotonic() + timeout
        with self.condition:
            while True:
                for item in list(self.events):
                    if item[0] == event and check(item[1]):
                        self.events.remove(item)
                        return item[1]
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    raise AssertionError(f"Timed out waiting for {event}: {list(self.events)}")
                self.condition.wait(remaining)

    def has(self, event, check=lambda body: True):
        with self.condition:
            return any(e == event and check(b) for e, b in self.events)


class ProtocolTests(unittest.TestCase):
    def test_01_chinese_utf8_roundtrip(self):
        packet = make_packet("CHAT", dict(text="你好，局域网！Hello 🌏\n第二行"))
        self.assertEqual(decode(encode(packet)), packet)

    def test_02_tampering_detected(self):
        packet = make_packet("CHAT", dict(text="原文"))
        packet["body"]["text"] = "篡改"
        with self.assertRaises(ProtocolError) as ctx:
            decode(canonical(packet))
        self.assertEqual(ctx.exception.code, "BAD_CHECKSUM")

    def test_03_malformed_envelopes(self):
        for raw in (b"[]", b"{", b"\xff", b'{"v":1,"v":1}', b'{"x":NaN}'):
            with self.subTest(raw=raw), self.assertRaises(ProtocolError):
                decode(raw)
        with self.assertRaises(ProtocolError):
            decode(b" " * (MAX_FRAME + 1))


class NativeIntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory(prefix="lan_chat_test_")
        cls.db = Path(cls.temp.name) / "中文账户" / "accounts.json"
        with socket.socket() as probe:
            probe.bind(("127.0.0.1", 0))
            cls.port = probe.getsockname()[1]
        cls.logs = []
        cls.server = NativeServer("127.0.0.1", cls.port, cls.db, "127.0.0.1", cls.logs.append)
        cls.server.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.stop()
        cls.temp.cleanup()

    def setUp(self):
        self.clients = []
        self.raw = []

    def tearDown(self):
        for client in self.clients:
            client.close()
        for sock in self.raw:
            sock.close()

    def account(self, name, multicast=True):
        inbox = Inbox()
        client = ChatClient(inbox.put, interface="127.0.0.1", multicast=multicast)
        self.clients.append(client)
        client.connect("127.0.0.1", self.port)
        client.register(name, "demo123456")
        result = inbox.wait("result", lambda b: b["action"] == "REGISTER")
        self.assertTrue(result["ok"], result)
        client.login(name, "demo123456")
        inbox.wait("result", lambda b: b["action"] == "LOGIN")
        return client, inbox

    def socket(self):
        sock = socket.create_connection(("127.0.0.1", self.port), timeout=3)
        self.raw.append(sock)
        return sock

    def response(self, sock, task, body=None):
        send_frame(sock, make_packet(task, body))
        return recv_frame(sock)

    def test_04_register_login_password_and_persistence(self):
        client, box = self.account("账户校验")
        stored = json.loads(self.db.read_text(encoding="utf-8"))["账户校验"]
        self.assertNotIn("demo123456", self.db.read_text(encoding="utf-8"))
        expected = hashlib.pbkdf2_hmac("sha256", b"demo123456", bytes.fromhex(stored["salt"]), 200000).hex()
        self.assertEqual(stored["digest"], expected)
        sock = self.socket()
        self.assertFalse(self.response(sock, "REGISTER", dict(name="账户校验", password="demo123456"))["body"]["ok"])
        self.assertEqual(self.response(sock, "LOGIN", dict(name="账户校验", password="wrong123"))["body"]["code"], "AUTH_FAILED")
        self.assertEqual(self.response(sock, "LOGIN", dict(name="账户校验", password="demo123456"))["body"]["code"], "ALREADY_ONLINE")
        client.logout()
        box.wait("result", lambda b: b["action"] == "LOGOUT")
        self.assertTrue(self.response(sock, "LOGIN", dict(name="账户校验", password="demo123456"))["body"]["ok"])

    def test_05_real_multicast_chinese_and_dedup(self):
        a, ia = self.account("组播甲")
        b, ib = self.account("组播乙")
        text = "中文群聊：你好，世界！English 123 🌏"
        a.chat(text)
        ma = ia.wait("message", lambda m: m["text"] == text)
        mb = ib.wait("message", lambda m: m["text"] == text)
        self.assertEqual(ma["transport"], "UDP 组播")
        self.assertEqual(mb["transport"], "UDP 组播")
        self.assertEqual(ma["id"], mb["id"])
        # A repeated server packet must not display twice.
        repeated = make_packet("MESSAGE", {k: v for k, v in ma.items() if k not in {"id", "ts", "transport"}})
        repeated["id"] = ma["id"]
        a._message(repeated, "TCP")
        self.assertFalse(ia.has("message", lambda m: m["text"] == text))

    def test_06_selected_multiple_recipient_isolation(self):
        a, ia = self.account("定向甲")
        b, ib = self.account("定向乙")
        c, ic = self.account("定向丙")
        d, id_ = self.account("旁观丁")
        a.chat("仅乙丙收到", ["定向乙", "定向丙"])
        for box in (ia, ib, ic):
            message = box.wait("message", lambda m: m["text"] == "仅乙丙收到")
            self.assertEqual(message["transport"], "TCP")
            self.assertEqual(message["mode"], "selected")
        with self.assertRaises(AssertionError):
            id_.wait("message", lambda m: m["text"] == "仅乙丙收到", timeout=0.35)

    def test_07_multicast_loss_tcp_repair(self):
        a, ia = self.account("补发甲")
        b, ib = self.account("补发乙", multicast=False)
        start = time.monotonic()
        a.chat("关闭组播仍收到")
        msg = ib.wait("message", lambda m: m["text"] == "关闭组播仍收到")
        self.assertEqual(msg["transport"], "TCP")
        self.assertGreaterEqual(time.monotonic() - start, 0.65)

    def test_08_invalid_task_and_corruption_recover(self):
        sock = self.socket()
        self.assertEqual(self.response(sock, "TASK_DOES_NOT_EXIST")["body"]["code"], "INVALID_TASK")
        bad = make_packet("PING")
        bad["body"]["tampered"] = True
        raw = canonical(bad)
        sock.sendall(struct.pack("!I", len(raw)) + raw)
        self.assertEqual(recv_frame(sock)["body"]["code"], "BAD_CHECKSUM")
        self.assertEqual(self.response(sock, "PING")["type"], "PONG")

    def test_09_fragmented_and_coalesced_tcp_frames(self):
        sock = self.socket()
        one, two = encode(make_packet("PING")), encode(make_packet("PING"))
        frame = struct.pack("!I", len(one)) + one + struct.pack("!I", len(two)) + two
        for index in range(0, len(frame), 7):
            sock.sendall(frame[index:index+7])
        self.assertEqual(recv_frame(sock)["type"], "PONG")
        self.assertEqual(recv_frame(sock)["type"], "PONG")

    def test_10_malformed_packet_and_oversized_frame(self):
        sock = self.socket()
        for raw in (b"not JSON", b"\xff", b'{"v":1,"v":2}'):
            sock.sendall(struct.pack("!I", len(raw)) + raw)
            self.assertEqual(recv_frame(sock)["body"]["code"], "BAD_PACKET")
        self.assertEqual(self.response(sock, "CHAT", dict(text="匿名", mode="all"))["body"]["code"], "NOT_LOGGED_IN")
        sock.sendall(struct.pack("!I", MAX_FRAME + 1))
        self.assertEqual(recv_frame(sock)["body"]["code"], "FRAME_TOO_LARGE")
        self.assertEqual(sock.recv(1), b"")
        fresh = self.socket()
        self.assertEqual(self.response(fresh, "PING")["type"], "PONG")

    def test_11_bad_body_replay_and_roster_on_disconnect(self):
        a, ia = self.account("边界甲")
        b, ib = self.account("边界乙")
        ia.wait("roster", lambda m: "边界乙" in m["members"])
        for text, targets, code in [("", None, "BAD_BODY"), ("字" * 2001, None, "BAD_BODY"),
                                    ("你好", [], "NO_RECIPIENT"), ("你好", ["不存在"], "NO_RECIPIENT")]:
            a.chat(text, targets)
            ia.wait("error", lambda m: m["code"] == code)
        a.request("CHAT", dict(text="类型错误", mode="selected", targets=[123]))
        ia.wait("error", lambda m: m["code"] == "BAD_BODY")
        b.close()
        ia.wait("roster", lambda m: "边界乙" not in m["members"])
        raw = self.socket()
        packet = make_packet("PING")
        send_frame(raw, packet)
        self.assertEqual(recv_frame(raw)["type"], "PONG")
        send_frame(raw, packet)
        self.assertEqual(recv_frame(raw)["body"]["code"], "REPLAY")

    def test_12_database_survives_restart(self):
        # Separate real process proves persistence independent of server memory.
        temp = tempfile.TemporaryDirectory(prefix="lan_persist_")
        with socket.socket() as probe:
            probe.bind(("127.0.0.1", 0))
            port = probe.getsockname()[1]
        server = NativeServer("127.0.0.1", port, Path(temp.name) / "accounts.json", "127.0.0.1", lambda x: None)
        try:
            server.start()
            with socket.create_connection(("127.0.0.1", port), timeout=3) as s:
                self.assertTrue(self.response(s, "REGISTER", dict(name="持久化", password="persist123"))["body"]["ok"])
            server.stop()
            server.start()
            with socket.create_connection(("127.0.0.1", port), timeout=3) as s:
                self.assertTrue(self.response(s, "LOGIN", dict(name="持久化", password="persist123"))["body"]["ok"])
        finally:
            server.stop()
            temp.cleanup()


if __name__ == "__main__":
    unittest.main(verbosity=2)
