"""Launch and monitor the bundled C++ server without a console window."""
from pathlib import Path
import subprocess
import threading


class NativeServer:
    def __init__(self, host, port, db, interface, log=print, on_exit=lambda: None):
        self.host, self.port, self.db, self.interface = host, port, db, interface
        self.log, self.on_exit = log, on_exit
        self.process = None
        self.monitor = None

    def start(self):
        executable = Path(__file__).resolve().parent.parent / "bin" / "chat_server.exe"
        if not executable.exists():
            raise OSError("找不到 C++ 服务端，请先运行 build_server.bat")
        self.process = subprocess.Popen(
            [str(executable), "--host", self.host, "--port", str(self.port),
             "--interface", self.interface, "--db", str(self.db)],
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            text=True, encoding="utf-8", errors="replace",
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        ready = threading.Event()
        failure = []
        process = self.process

        def monitor():
            for line in process.stdout:
                line = line.rstrip()
                self.log(line)
                if line.startswith("READY "):
                    ready.set()
                if line.startswith("FATAL "):
                    failure.append(line)
            process.wait()
            process.stdout.close()
            ready.set()
            self.on_exit()
        self.monitor = threading.Thread(target=monitor, daemon=True)
        self.monitor.start()
        if not ready.wait(5) or failure or self.process.poll() is not None:
            self.stop()
            raise OSError(failure[0] if failure else "C++ 服务端未能启动，请检查端口和网卡地址")

    def stop(self):
        if self.process and self.process.poll() is None:
            self.process.terminate()
            try:
                self.process.wait(timeout=3)
            except subprocess.TimeoutExpired:
                self.process.kill()
                self.process.wait(timeout=3)
        if self.monitor and self.monitor is not threading.current_thread():
            self.monitor.join(timeout=2)

