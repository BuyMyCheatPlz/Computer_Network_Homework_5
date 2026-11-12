"""Record the real GUI with real C++/Python network participants.

Run after make_narration.ps1, using the bundled Python runtime with media deps.
Only the demo application's own window is captured. No desktop-wide capture.
"""
import ctypes
import json
from pathlib import Path
import queue
import socket
import struct
import subprocess
import sys
import tempfile
import threading
import time
import tkinter as tk
from tkinter import scrolledtext, ttk
import wave

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tools" / "media_runtime"))
from lan_chat.client import ChatClient
from lan_chat.gui import ChatApp
from lan_chat.protocol import canonical, make_packet


def build_audio():
    parts = json.loads((ROOT / "tools/demo_segments.json").read_text(encoding="utf-8"))
    cursor = 0
    audio = bytearray()
    params = None
    for part in parts:
        with wave.open(str(ROOT / "docs/demo_audio" / (part["key"] + ".wav")), "rb") as stream:
            if params is None:
                params = stream.getparams()
            assert stream.getnchannels() == params.nchannels
            assert stream.getsampwidth() == params.sampwidth
            assert stream.getframerate() == params.framerate
            samples = stream.readframes(stream.getnframes())
        duration = len(samples) / (params.framerate * params.sampwidth * params.nchannels)
        part["start"] = cursor
        part["duration"] = max(part["seconds"], duration + 1.0)
        frames = round(part["duration"] * params.framerate)
        part["duration"] = frames / params.framerate
        part["end"] = cursor + part["duration"]
        target_size = frames * params.sampwidth * params.nchannels
        audio.extend(samples)
        audio.extend(b"\0" * (target_size - len(samples)))
        cursor = part["end"]
    assert cursor < 179, f"Narration too long: {cursor}"
    output = ROOT / "docs/演示讲解.wav"
    with wave.open(str(output), "wb") as stream:
        stream.setparams(params)
        stream.writeframes(audio)
    (ROOT / "docs/演示时间轴.json").write_text(json.dumps(parts, ensure_ascii=False, indent=2), encoding="utf-8")
    # SRT matches the real stage durations; also serves as an accessible transcript.
    def stamp(value):
        ms = round(value * 1000)
        return f"{ms//3600000:02}:{ms//60000%60:02}:{ms//1000%60:02},{ms%1000:03}"
    (ROOT / "演示字幕.srt").write_text("\n\n".join(
        f"{i+1}\n{stamp(p['start'])} --> {stamp(p['end'])}\n{p['title']}\n{p['text']}" for i, p in enumerate(parts)), encoding="utf-8-sig")
    return parts, output


class Demo:
    def __init__(self):
        ctypes.windll.shcore.SetProcessDpiAwareness(1)
        self.parts, self.audio = build_audio()
        self.temp = tempfile.TemporaryDirectory(prefix="chat_demo_")
        self.root = tk.Tk()
        self.root.tk.call("tk", "scaling", 1.333333)
        self.app = ChatApp(self.root, data=self.temp.name, title="作业5演示")
        self.root.geometry("1280x720+40+40")
        self.root.attributes("-topmost", True)
        self.app.interface.set("127.0.0.1")
        self.app.server_interface.set("127.0.0.1")
        with socket.socket() as probe:
            probe.bind(("127.0.0.1", 0))
            port = probe.getsockname()[1]
        self.app.port.set(str(port))
        self.app.server_port.set(str(port))
        self.port = port
        self.events = queue.Queue()
        self.clients = {}
        self.received = {name: [] for name in ("小周", "小陈", "旁听同学")}
        self.errors = []
        self.stage = tk.StringVar(value="准备运行演示")
        ttk.Label(self.root, textvariable=self.stage, foreground="#154c7b",
                  font=("Microsoft YaHei UI", 12, "bold")).pack(side="bottom", fill="x", padx=20, pady=4,
                  before=self.root.winfo_children()[0])
        self.validation = ttk.Frame(self.app.tabs, padding=12)
        self.app.tabs.add(self.validation, text="  其他真实客户端接收记录  ")
        ttk.Label(self.validation, text="三条独立 TCP 登录连接和 UDP 组播接收器 · 本机运行 · 所有记录均来自实际收包",
                  font=("Microsoft YaHei UI", 12, "bold")).pack(anchor="w", pady=(0, 12))
        row = ttk.Frame(self.validation)
        row.pack(fill="both", expand=True)
        self.logs = {}
        for name in self.received:
            frame = ttk.LabelFrame(row, text=name, padding=8)
            frame.pack(side="left", fill="both", expand=True, padx=5)
            widget = scrolledtext.ScrolledText(frame, width=28, wrap="word", state="disabled",
                                               font=("Microsoft YaHei UI", 11), padx=8, pady=8)
            widget.pack(fill="both", expand=True)
            self.logs[name] = widget
        ttk.Label(self.validation, text="定向消息“小周、小陈专属”：只应出现在前两列，旁听同学一列不应出现。",
                  foreground="#765b24").pack(anchor="w", pady=10)
        self.recorder = None
        self.recorder_log = None
        self.root.protocol("WM_DELETE_WINDOW", self.close)
        self.root.after(60, self.poll)
        self.root.after(1600, self.start)

    def worker(self, fn):
        def wrapped():
            try:
                fn()
            except Exception as exc:
                self.events.put(("DEMO", "failure", dict(message=f"{type(exc).__name__}: {exc}")))
        threading.Thread(target=wrapped, daemon=True).start()

    def start(self):
        import imageio_ffmpeg
        ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
        self.recorder_log = open(ROOT / "docs/录屏验证日志.txt", "w", encoding="utf-8")
        self.recorder = subprocess.Popen([
            ffmpeg, "-y", "-f", "gdigrab", "-framerate", "12", "-draw_mouse", "0",
            "-i", "title=作业5演示", "-i", str(self.audio),
            "-vf", "scale=1280:720:force_original_aspect_ratio=decrease,pad=1280:720:(ow-iw)/2:(oh-ih)/2",
            "-c:v", "libx264", "-preset", "veryfast", "-crf", "23", "-pix_fmt", "yuv420p",
            "-c:a", "aac", "-b:a", "96k", "-t", str(self.parts[-1]["end"]), "-movflags", "+faststart",
            str(ROOT / "演示视频.mp4")], stdout=self.recorder_log, stderr=subprocess.STDOUT,
            creationflags=subprocess.CREATE_NO_WINDOW)
        for part in self.parts:
            self.root.after(round(part["start"] * 1000) + 500, lambda p=part: self.stage_action(p))
        self.root.after(round(self.parts[-1]["end"] * 1000) + 2000, self.finish)

    def later(self, seconds, fn):
        self.root.after(round(seconds * 1000), fn)

    def main_send(self, text, selected=False):
        self.app.composer.delete("1.0", "end")
        self.app.composer.insert("1.0", text)
        self.app.send(selected)

    def remote(self, name):
        client = ChatClient(lambda e, b: self.events.put((name, e, b)), interface="127.0.0.1")
        self.clients[name] = client
        client.connect("127.0.0.1", self.port)
        client.register(name, "demo123456")
        # The same TCP connection processes REGISTER before LOGIN.
        client.login(name, "demo123456")

    def stage_action(self, part):
        print(f"STAGE {part['key']} online={self.app.client.name if self.app.client else None}", flush=True)
        self.stage.set(part["title"])
        key = part["key"]
        if key == "server":
            self.app.tabs.select(1)
            self.app.start_server()
        elif key == "accounts":
            self.app.tabs.select(0)
            self.app.username.set("小林")
            self.app.password.set("demo123456")
            self.app.auth("REGISTER")
            self.later(2, lambda: self.app.auth("LOGIN"))
            for i, name in enumerate(self.received):
                self.later(4 + i, lambda n=name: self.worker(lambda: self.remote(n)))
        elif key == "group":
            self.app.tabs.select(0)
            self.later(2, lambda: self.main_send("大家好！这是中文群聊。Hello LAN 2026！"))
            self.later(8, lambda: self.app.tabs.select(2))
        elif key == "selected":
            self.app.tabs.select(0)
            self.app.member_list.selection_clear(0, "end")
            for i, name in enumerate(self.app.members):
                if name in ("小周", "小陈"):
                    self.app.member_list.selection_set(i)
            self.later(2, lambda: self.main_send("小周、小陈专属：请一起核对实验结果。", True))
            self.later(8, lambda: self.app.tabs.select(2))
        elif key == "invalid":
            self.app.tabs.select(0)
            self.later(1, lambda: self.app.client.request("TASK_DOES_NOT_EXIST"))
            self.later(5, self.tamper)
            self.later(10, lambda: self.main_send("异常报文已被拒绝，正常群聊继续运行。"))
        elif key == "repair":
            self.app.tabs.select(2)
            self.clients["旁听同学"]._leave()
            self.later(2, lambda: self.main_send("补发验证：旁听同学退出组播后仍能接收。"))
        elif key == "logout":
            self.app.tabs.select(0)
            self.clients["小陈"].logout()
            self.later(6, self.app.logout)
            self.later(11, self.relogin)
        elif key == "summary":
            self.app.tabs.select(1)

    def relogin(self):
        self.app.password.set("demo123456")
        self.app.auth("LOGIN")

    def tamper(self):
        packet = make_packet("PING")
        packet["body"]["modified"] = "修改但不更新摘要"
        data = canonical(packet)
        with self.app.client.lock:
            self.app.client.sock.sendall(struct.pack("!I", len(data)) + data)

    def poll(self):
        while True:
            try:
                name, event, body = self.events.get_nowait()
            except queue.Empty:
                break
            if event == "failure":
                self.errors.append(body)
                self.stage.set("演示错误：" + body["message"])
            if name not in self.logs:
                continue
            if event == "message":
                self.received[name].append(body)
                mode = "群聊" if body["mode"] == "all" else "定向"
                text = f"{body['sender']} [{mode} / {body['transport']}]\n{body['text']}\n\n"
            elif event in ("result", "transport", "warning", "error"):
                text = body.get("message", "") + "\n"
            else:
                continue
            widget = self.logs[name]
            widget.configure(state="normal")
            widget.insert("end", text)
            widget.see("end")
            widget.configure(state="disabled")
        self.root.after(60, self.poll)

    def finish(self):
        if self.recorder:
            code = self.recorder.poll()
            if code is None:
                self.later(1, self.finish)
                return
            if code:
                self.errors.append(dict(message=f"ffmpeg exited {code}"))
        # Persist real evidence even if a check fails, then always close resources.
        (ROOT / "docs/演示实测记录.json").write_text(json.dumps(self.received, ensure_ascii=False, indent=2), encoding="utf-8")
        problems = list(self.errors)
        for name in self.received:
            if not any("中文群聊" in m["text"] and m["transport"] == "UDP 组播" for m in self.received[name]):
                problems.append("Missing UDP group receipt: " + name)
        if any(m["mode"] == "selected" for m in self.received["旁听同学"]):
            problems.append("Recipient isolation failed")
        if not all(any(m["mode"] == "selected" for m in self.received[n]) for n in ("小周", "小陈")):
            problems.append("Two selected recipients missing")
        if not any("补发验证" in m["text"] and m["transport"] == "TCP" for m in self.received["旁听同学"]):
            problems.append("TCP repair missing")
        print("DEMO FAILED: " + str(problems) if problems else "DEMO VERIFIED: multicast, two selected recipients, isolation, TCP repair, logout", flush=True)
        self.close()
        if problems:
            raise RuntimeError(problems)

    def close(self):
        if self.recorder and self.recorder.poll() is None:
            self.recorder.terminate()
            self.recorder.wait(timeout=5)
        if self.recorder_log:
            self.recorder_log.close()
        for client in self.clients.values():
            client.close()
        if self.app.client:
            self.app.client.close()
        if self.app.server:
            self.app.server.stop()
        self.root.destroy()
        self.temp.cleanup()


if __name__ == "__main__":
    demo = Demo()
    demo.root.mainloop()
