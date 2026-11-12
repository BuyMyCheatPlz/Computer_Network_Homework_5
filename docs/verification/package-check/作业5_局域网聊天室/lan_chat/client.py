"""Headless client used by both Tkinter and integration tests."""
from collections import deque
import socket
import threading

from .protocol import TCP_PORT, ProtocolError, decode, make_packet, recv_frame, send_frame


class ChatClient:
    def __init__(self, callback, interface="0.0.0.0", multicast=True):
        self.callback = callback
        self.interface, self.multicast = interface, multicast
        self.sock = self.udp = None
        self.name = self.room_id = None
        self.lock = threading.Lock()
        self.seen_lock = threading.Lock()
        self.seen, self.order = set(), deque()
        self.stopped = threading.Event()
        self.udp_stopped = threading.Event()

    def connect(self, host, port=TCP_PORT):
        self.sock = socket.create_connection((host, port), timeout=5)
        self.sock.settimeout(None)
        threading.Thread(target=self._receive, daemon=True).start()
        threading.Thread(target=self._heartbeat, daemon=True).start()

    def request(self, task, body=None):
        packet = make_packet(task, body)
        with self.lock:
            if not self.sock or self.stopped.is_set():
                raise OSError("尚未连接服务器")
            send_frame(self.sock, packet)
        return packet["id"]

    def register(self, name, password):
        return self.request("REGISTER", dict(name=name, password=password))

    def login(self, name, password):
        return self.request("LOGIN", dict(name=name, password=password))

    def chat(self, text, targets=None):
        return self.request("CHAT", dict(text=text, mode="selected" if targets is not None else "all",
                                         targets=targets or []))

    def logout(self):
        return self.request("LOGOUT")

    def _heartbeat(self):
        while not self.stopped.wait(4):
            try:
                self.request("PING")
            except OSError:
                self.close()
                return

    def _receive(self):
        try:
            while not self.stopped.is_set():
                try:
                    packet = recv_frame(self.sock)
                except ProtocolError as exc:
                    self.callback("warning", dict(message=str(exc)))
                    if exc.code == "FRAME_TOO_LARGE":
                        break
                    continue
                body = packet["body"]
                if packet["type"] == "RESULT" and body.get("ok"):
                    if body.get("action") == "LOGIN":
                        self.name, self.room_id = body["name"], body["room_id"]
                        self._join(body["group"], body["udp_port"])
                    elif body.get("action") == "LOGOUT":
                        self.name = self.room_id = None
                        self._leave()
                if packet["type"] == "MESSAGE":
                    self._message(packet, "TCP")
                elif packet["type"] != "PONG":
                    self.callback(packet["type"].lower(), body)
        except (OSError, EOFError) as exc:
            if not self.stopped.is_set():
                self.callback("warning", dict(message=f"连接中断：{exc}"))
        finally:
            self.close()

    def _join(self, group, port):
        self._leave()
        if not self.multicast:
            self.callback("transport", dict(message="组播已关闭，使用 TCP 补发"))
            return
        udp = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
        try:
            udp.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            udp.bind(("", port))
            udp.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP,
                           socket.inet_aton(group) + socket.inet_aton(self.interface))
            udp.settimeout(0.5)
        except OSError as exc:
            udp.close()
            self.callback("warning", dict(message=f"加入组播失败，自动使用 TCP 补发：{exc}"))
            return
        self.udp = udp
        self.udp_stopped = threading.Event()
        threading.Thread(target=self._receive_udp, args=(udp, self.udp_stopped), daemon=True).start()
        self.callback("transport", dict(message=f"已加入组播 {group}:{port}"))

    def _leave(self):
        self.udp_stopped.set()
        if self.udp:
            self.udp.close()
            self.udp = None

    def _receive_udp(self, udp, stopped):
        while not stopped.is_set() and not self.stopped.is_set():
            try:
                data, _ = udp.recvfrom(32769)
                packet = decode(data)
                if packet["type"] == "MESSAGE":
                    self._message(packet, "UDP 组播")
            except socket.timeout:
                continue
            except ProtocolError as exc:
                self.callback("warning", dict(message=f"丢弃异常组播：{exc}"))
            except OSError:
                break

    def _message(self, packet, transport):
        body, mid = packet["body"], packet["id"]
        if (body.get("room_id") != self.room_id or self.name not in body.get("recipients", [])
                or not isinstance(body.get("text"), str)):
            return
        if body.get("mode") == "all":
            try:
                self.request("ACK", dict(message_id=mid))
            except OSError:
                return
        with self.seen_lock:
            if mid in self.seen:
                return
            self.seen.add(mid)
            self.order.append(mid)
            if len(self.order) > 2048:
                self.seen.discard(self.order.popleft())
        self.callback("message", dict(body, transport=transport, id=mid, ts=packet["ts"]))

    def close(self):
        with self.lock:
            if self.stopped.is_set():
                return
            self.stopped.set()
            self._leave()
            if self.sock:
                try:
                    self.sock.shutdown(socket.SHUT_RDWR)
                except OSError:
                    pass
                self.sock.close()
        self.name = self.room_id = None
        self.callback("disconnected", {})
