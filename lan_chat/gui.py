"""Chinese Tkinter GUI. Network workers never access Tk widgets."""
import argparse
from datetime import datetime
from pathlib import Path
import queue
import threading
import tkinter as tk
from tkinter import messagebox, scrolledtext, ttk

from .client import ChatClient
from .protocol import MAX_TEXT, TCP_PORT, ProtocolError
from .native_server import NativeServer


class ChatApp:
    def __init__(self, root, data="data", title="局域网聊天室"):
        self.root, self.data = root, Path(data)
        self.root.title(title)
        self.root.geometry("1080x750")
        self.root.minsize(850, 650)
        self.events = queue.Queue()
        self.client = self.server = None
        self.busy = False
        self.generation = 0
        self.members = []
        self.host = tk.StringVar(value="127.0.0.1")
        self.port = tk.StringVar(value=str(TCP_PORT))
        self.interface = tk.StringVar(value="0.0.0.0")
        self.username = tk.StringVar()
        self.password = tk.StringVar()
        self.status = tk.StringVar(value="未登录 · 在服务器电脑启动服务后连接")
        self.server_host = tk.StringVar(value="0.0.0.0")
        self.server_port = tk.StringVar(value=str(TCP_PORT))
        self.server_interface = tk.StringVar(value="0.0.0.0")
        style = ttk.Style()
        style.theme_use("clam")
        style.configure("TFrame", background="#f3f6fa")
        style.configure("TLabel", background="#f3f6fa", font=("Microsoft YaHei UI", 10))
        style.configure("TButton", font=("Microsoft YaHei UI", 10), padding=(10, 6))
        style.configure("Header.TLabel", font=("Microsoft YaHei UI", 22, "bold"), foreground="#173c66")
        style.configure("TLabelframe", background="#f3f6fa")
        style.configure("TLabelframe.Label", background="#f3f6fa", font=("Microsoft YaHei UI", 10, "bold"))
        self._build()
        root.protocol("WM_DELETE_WINDOW", self.close)
        root.after(60, self._poll)

    def _build(self):
        outer = ttk.Frame(self.root, padding=18)
        outer.pack(fill="both", expand=True)
        ttk.Label(outer, text="局域网聊天室", style="Header.TLabel").pack(anchor="w")
        ttk.Label(outer, text="中文交流 · UDP 组播群聊 · 多人定向发送 · SHA-256 完整性校验").pack(anchor="w", pady=(4, 14))
        tabs = ttk.Notebook(outer)
        tabs.pack(fill="both", expand=True)
        chat, monitor = ttk.Frame(tabs, padding=12), ttk.Frame(tabs, padding=12)
        tabs.add(chat, text="  聊天室  ")
        tabs.add(monitor, text="  服务器管理  ")
        self.tabs = tabs
        box = ttk.LabelFrame(chat, text="连接与账号", padding=10)
        box.pack(fill="x")
        fields = [("服务器 IPv4", self.host, 17), ("TCP 端口", self.port, 7),
                  ("本机组播 IPv4", self.interface, 17)]
        self.connection_entries = []
        for col, (label, var, width) in enumerate(fields):
            ttk.Label(box, text=label).grid(row=0, column=2*col, padx=(0, 5))
            entry = ttk.Entry(box, textvariable=var, width=width)
            entry.grid(row=0, column=2*col+1, padx=(0, 15))
            self.connection_entries.append(entry)
        ttk.Label(box, text="用户名").grid(row=1, column=0, pady=(10, 0), sticky="w")
        self.name_entry = ttk.Entry(box, textvariable=self.username, width=17)
        self.name_entry.grid(row=1, column=1, pady=(10, 0), sticky="w")
        ttk.Label(box, text="密码").grid(row=1, column=2, pady=(10, 0), sticky="w")
        self.pass_entry = ttk.Entry(box, textvariable=self.password, show="●", width=17)
        self.pass_entry.grid(row=1, column=3, pady=(10, 0), sticky="w")
        actions = ttk.Frame(box)
        actions.grid(row=1, column=4, columnspan=2, pady=(10, 0), sticky="w")
        self.register_button = ttk.Button(actions, text="注册", command=lambda: self.auth("REGISTER"))
        self.register_button.pack(side="left", padx=(0, 5))
        self.login_button = ttk.Button(actions, text="登录", command=lambda: self.auth("LOGIN"))
        self.login_button.pack(side="left", padx=(0, 5))
        self.logout_button = ttk.Button(actions, text="注销", command=self.logout, state="disabled")
        self.logout_button.pack(side="left")
        ttk.Label(chat, textvariable=self.status, foreground="#245780").pack(fill="x", pady=9)
        body = ttk.Frame(chat)
        history_box = ttk.LabelFrame(body, text="会话记录", padding=8)
        history_box.pack(side="left", fill="both", expand=True, padx=(0, 12))
        self.history = scrolledtext.ScrolledText(history_box, height=12, width=60, wrap="word", state="disabled",
                              font=("Microsoft YaHei UI", 10), bg="white", relief="flat", padx=10, pady=8)
        self.history.pack(fill="both", expand=True)
        self.history.tag_configure("system", foreground="#6d7784")
        self.history.tag_configure("sender", foreground="#175c8c", font=("Microsoft YaHei UI", 10, "bold"))
        self.history.tag_configure("private", foreground="#84602a")
        self.history.tag_configure("error", foreground="#b13e40")
        sidebar = ttk.LabelFrame(body, text="在线成员", padding=8)
        sidebar.pack(side="right", fill="y")
        self.member_label = ttk.Label(sidebar, text="0 人在线")
        self.member_label.pack(anchor="w", pady=(0, 6))
        self.member_list = tk.Listbox(sidebar, selectmode="multiple", exportselection=False,
                                width=19, font=("Microsoft YaHei UI", 11), relief="flat",
                                selectbackground="#265f96", activestyle="none")
        self.member_list.pack(fill="both", expand=True)
        ttk.Label(sidebar, text="单击可多选\n选中成员后定向发送", foreground="#677485").pack(anchor="w", pady=(8, 0))
        composer = ttk.Frame(chat)
        self.composer = tk.Text(composer, height=3, wrap="word", font=("Microsoft YaHei UI", 11),
                                relief="solid", borderwidth=1, padx=8, pady=6)
        self.composer.pack(side="left", fill="x", expand=True, padx=(0, 10))
        self.composer.bind("<Control-Return>", lambda event: self.send(False))
        buttons = ttk.Frame(composer)
        buttons.pack(side="right", fill="y")
        self.all_button = ttk.Button(buttons, text="群发  Ctrl+Enter", command=lambda: self.send(False), state="disabled")
        self.all_button.pack(fill="x", pady=(0, 5))
        self.selected_button = ttk.Button(buttons, text="发送给选中成员", command=lambda: self.send(True), state="disabled")
        self.selected_button.pack(fill="x")
        ttk.Label(chat, text="每条最多 2000 字 · Enter 换行 · 注销退出登录，账号仍保留", foreground="#677485").pack(side="bottom", anchor="w", pady=(7, 0))
        composer.pack(side="bottom", fill="x", pady=(12, 0))
        body.pack(fill="both", expand=True)
        config = ttk.LabelFrame(monitor, text="服务配置", padding=12)
        config.pack(fill="x")
        for row, (label, var) in enumerate([("监听 IPv4", self.server_host), ("TCP 端口", self.server_port),
                                          ("组播出口 IPv4", self.server_interface)]):
            ttk.Label(config, text=label).grid(row=row, column=0, sticky="w", pady=5)
            ttk.Entry(config, textvariable=var, width=24).grid(row=row, column=1, padx=10, pady=5)
        self.start_button = ttk.Button(config, text="启动服务器", command=self.start_server)
        self.start_button.grid(row=0, column=2, padx=14)
        self.stop_button = ttk.Button(config, text="停止服务器", command=self.stop_server, state="disabled")
        self.stop_button.grid(row=1, column=2, padx=14)
        ttk.Label(monitor, text="同一局域网运行一个服务器。其他电脑填写服务器的局域网 IPv4；多网卡时填写实际网卡地址。",
                  wraplength=840).pack(anchor="w", pady=12)
        self.server_log = scrolledtext.ScrolledText(monitor, state="disabled", wrap="word",
                    font=("Consolas", 11), bg="#16283d", fg="#d9e9f8", padx=12, pady=12)
        self.server_log.pack(fill="both", expand=True)

    def append(self, text, tag="system"):
        self.history.configure(state="normal")
        self.history.insert("end", text + "\n", tag)
        self.history.see("end")
        self.history.configure(state="disabled")

    def _online(self, online):
        for widget in (self.name_entry, self.pass_entry, self.register_button, self.login_button, *self.connection_entries):
            widget.configure(state="disabled" if online else "normal")
        for widget in (self.logout_button, self.all_button, self.selected_button):
            widget.configure(state="normal" if online else "disabled")

    def _validate_connection(self):
        port = int(self.port.get())
        if not 1 <= port <= 65535:
            raise ValueError("端口须在 1 至 65535 之间")
        return self.host.get().strip(), port, self.interface.get().strip()

    def auth(self, action):
        if self.busy:
            return
        name, password = self.username.get().strip(), self.password.get()
        if not name or not password:
            self.append("请填写用户名和密码", "error")
            return
        try:
            host, port, interface = self._validate_connection()
        except ValueError as exc:
            self.append(str(exc), "error")
            return
        # One connection per auth attempt avoids stale server/interface settings.
        if self.client:
            self.generation += 1
            self.client.close()
        self.generation += 1
        generation = self.generation
        self.busy = True
        self.status.set("正在连接服务器…")
        self.client = ChatClient(lambda event, body: self.events.put((generation, event, body)), interface)
        client = self.client

        def work():
            try:
                client.connect(host, port)
                client.request(action, dict(name=name, password=password))
            except (OSError, ValueError) as exc:
                self.events.put((generation, "warning", dict(message=str(exc))))
                client.close()
        threading.Thread(target=work, daemon=True).start()

    def logout(self):
        try:
            self.client.logout()
        except (OSError, AttributeError) as exc:
            self.append(str(exc), "error")

    def send(self, selected):
        text = self.composer.get("1.0", "end-1c")
        targets = [self.members[i] for i in self.member_list.curselection()] if selected else None
        if selected and not targets:
            self.append("请先在成员列表中选择一个或多个接收人", "error")
            return "break"
        if not text.strip() or len(text) > MAX_TEXT:
            self.append("消息须为 1 至 2000 个字符且不能全为空白", "error")
            return "break"
        try:
            self.client.chat(text, targets)
            self.composer.delete("1.0", "end")
        except (OSError, AttributeError, ProtocolError) as exc:
            self.append(f"发送失败：{exc}", "error")
        return "break"

    def start_server(self):
        if self.server:
            return
        try:
            port = int(self.server_port.get())
            if not 1 <= port <= 65535:
                raise ValueError("端口须在 1 至 65535 之间")
            self.server = NativeServer(host=self.server_host.get().strip(), port=port,
                     interface=self.server_interface.get().strip(), db=self.data / "accounts.json",
                     log=lambda text: self.events.put((None, "server_log", dict(message=text))),
                     on_exit=lambda: self.events.put((None, "server_stopped", {})))
            self.server.start()
            self.start_button.configure(state="disabled")
            self.stop_button.configure(state="normal")
        except (OSError, ValueError) as exc:
            self.server = None
            messagebox.showerror("服务器启动失败", str(exc), parent=self.root)

    def stop_server(self):
        server = self.server
        if server:
            threading.Thread(target=server.stop).start()
        self.stop_button.configure(state="disabled")

    def _poll(self):
        for _ in range(150):
            try:
                generation, event, body = self.events.get_nowait()
            except queue.Empty:
                break
            if generation is not None and generation != self.generation:
                continue
            if event == "server_stopped":
                if self.server and self.server.process.poll() is not None:
                    self.server = None
                    self.start_button.configure(state="normal")
                    self.stop_button.configure(state="disabled")
            elif event == "server_log":
                self.server_log.configure(state="normal")
                self.server_log.insert("end", datetime.now().strftime("%H:%M:%S  ") + body["message"] + "\n")
                self.server_log.see("end")
                self.server_log.configure(state="disabled")
            elif event == "result":
                self.busy = False
                action = body.get("action")
                if action == "CHAT":
                    continue
                self.append(body.get("message", ""))
                if body.get("ok") and action == "LOGIN":
                    self._online(True)
                    self.password.set("")
                    self.status.set(f"已登录：{body['name']} · 群发使用 UDP 组播，未确认消息自动补发")
                elif action == "LOGOUT":
                    self._online(False)
                    self.member_list.delete(0, "end")
                    self.members = []
                    self.member_label.configure(text="0 人在线")
                    self.status.set("已注销 · 可以重新登录或切换账号")
                elif action == "REGISTER":
                    self.status.set("注册成功，请点击登录" if body.get("ok") else "注册未完成，请检查提示")
            elif event == "roster":
                chosen = {self.members[i] for i in self.member_list.curselection()}
                self.members = body["members"]
                self.member_list.delete(0, "end")
                for i, name in enumerate(self.members):
                    self.member_list.insert("end", name + ("（我）" if self.client and name == self.client.name else ""))
                    if name in chosen:
                        self.member_list.selection_set(i)
                self.member_label.configure(text=f"{len(self.members)} 人在线")
            elif event == "message":
                when = datetime.fromtimestamp(body["ts"] / 1000).strftime("%H:%M:%S")
                scope = "群聊" if body["mode"] == "all" else "定向 → " + "、".join(body["targets"])
                self.append(f"{body['sender']}  {when}  [{scope} · {body['transport']}]", "sender" if body["mode"] == "all" else "private")
                self.append(body["text"] + "\n", "content")
            elif event in {"error", "warning"}:
                self.busy = False
                self.append(body.get("message", "未知错误") + (f" [{body['code']}]" if "code" in body else ""), "error")
                if not self.client or not self.client.name:
                    self.status.set("操作未完成，请检查提示后重试")
            elif event == "transport":
                self.append(body["message"])
            elif event == "disconnected":
                self.busy = False
                self._online(False)
                self.members = []
                self.member_list.delete(0, "end")
                self.member_label.configure(text="0 人在线")
                self.status.set("连接已关闭 · 可以重新登录")
        self.root.after(60, self._poll)

    def close(self):
        if self.client:
            self.client.close()
        if self.server:
            self.server.stop()
        self.root.destroy()


def main():
    parser = argparse.ArgumentParser(description="局域网聊天室图形界面")
    parser.add_argument("--data", default="data")
    args = parser.parse_args()
    root = tk.Tk()
    ChatApp(root, args.data)
    root.mainloop()


if __name__ == "__main__":
    main()
