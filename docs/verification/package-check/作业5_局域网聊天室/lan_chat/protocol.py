"""LCP/1 framing and integrity checks shared by TCP and UDP."""
import hashlib
import hmac
import json
import math
import re
import struct
import time
import uuid

MAX_FRAME = 32768
MAX_TEXT = 2000
GROUP = "239.255.42.99"
UDP_PORT = 45861
TCP_PORT = 45860


class ProtocolError(ValueError):
    def __init__(self, code, message):
        super().__init__(message)
        self.code = code


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True,
                      separators=(",", ":"), allow_nan=False).encode("utf-8")


def make_packet(task, body=None):
    obj = dict(v=1, id=uuid.uuid4().hex, type=task, ts=int(time.time() * 1000), body=body or {})
    obj["checksum"] = hashlib.sha256(canonical(obj)).hexdigest()
    return obj


def encode(packet):
    data = canonical(packet)
    if len(data) > MAX_FRAME:
        raise ProtocolError("FRAME_TOO_LARGE", "报文超过 32768 字节")
    return data


def _pairs(items):
    result = {}
    for key, value in items:
        if key in result:
            raise ValueError("duplicate key")
        result[key] = value
    return result


def decode(data):
    if len(data) > MAX_FRAME:
        raise ProtocolError("FRAME_TOO_LARGE", "报文过长")
    try:
        obj = json.loads(data.decode("utf-8"), object_pairs_hook=_pairs,
                         parse_constant=lambda x: (_ for _ in ()).throw(ValueError(x)))
        if not isinstance(obj, dict) or set(obj) != {"v", "id", "type", "ts", "body", "checksum"}:
            raise ValueError("fields")
        if type(obj["v"]) is not int or obj["v"] != 1:
            raise ValueError("version")
        if not isinstance(obj["id"], str) or not re.fullmatch(r"[0-9a-f]{32}", obj["id"]):
            raise ValueError("id")
        if not isinstance(obj["type"], str) or not 1 <= len(obj["type"]) <= 40:
            raise ValueError("type")
        if type(obj["ts"]) is not int or not 0 <= obj["ts"] <= 9007199254740991:
            raise ValueError("timestamp")
        if not isinstance(obj["body"], dict):
            raise ValueError("body")
        checksum = obj["checksum"]
        if not isinstance(checksum, str) or not re.fullmatch(r"[0-9a-f]{64}", checksum):
            raise ValueError("checksum")
        unsigned = {k: v for k, v in obj.items() if k != "checksum"}
        expected = hashlib.sha256(canonical(unsigned)).hexdigest()
        if not hmac.compare_digest(checksum, expected):
            raise ProtocolError("BAD_CHECKSUM", "完整性校验失败，报文已拒绝")
        return obj
    except ProtocolError:
        raise
    except (ValueError, TypeError, UnicodeError, RecursionError, OverflowError) as exc:
        raise ProtocolError("BAD_PACKET", "报文语法或字段格式无效") from exc


def send_frame(sock, packet):
    data = encode(packet)
    sock.sendall(struct.pack("!I", len(data)) + data)


def recv_exact(sock, size):
    data = bytearray()
    while len(data) < size:
        block = sock.recv(size - len(data))
        if not block:
            raise EOFError("连接已关闭")
        data.extend(block)
    return bytes(data)


def recv_frame(sock):
    size = struct.unpack("!I", recv_exact(sock, 4))[0]
    if not 1 <= size <= MAX_FRAME:
        raise ProtocolError("FRAME_TOO_LARGE", "TCP 帧长度不合法")
    return decode(recv_exact(sock, size))
