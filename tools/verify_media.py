"""Decode the finished MP4, inspect streams and export evidence frames."""
import json
from pathlib import Path
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools/media_runtime"))
import imageio_ffmpeg

ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
video = ROOT / "演示视频.mp4"
probe = subprocess.run([ffmpeg, "-hide_banner", "-i", str(video)], capture_output=True).stderr.decode("utf-8", "replace")
match = re.search(r"Duration: (\d+):(\d+):([\d.]+)", probe)
duration = int(match[1])*3600 + int(match[2])*60 + float(match[3])
assert duration < 180
assert re.search(r"Video: h264.*1280x720", probe)
assert "Audio: aac" in probe
decode = subprocess.run([ffmpeg, "-v", "error", "-i", str(video), "-f", "null", "-"], capture_output=True)
assert decode.returncode == 0 and not decode.stderr, decode.stderr
volume = subprocess.run([ffmpeg, "-hide_banner", "-i", str(video), "-vn", "-af", "volumedetect", "-f", "null", "-"], capture_output=True).stderr.decode("utf-8", "replace")
mean = float(re.search(r"mean_volume: ([\d.-]+) dB", volume)[1])
assert mean > -50, f"Narration too quiet: {mean} dB"
timeline = {p["key"]: p for p in json.loads((ROOT / "docs/演示时间轴.json").read_text(encoding="utf-8"))}
folder = ROOT / "docs/screenshots"
folder.mkdir(exist_ok=True)
for key, offset, name in [("server", 5, "服务器"), ("group", 5, "群聊"),
                          ("selected", 11, "定向隔离"), ("invalid", 8, "异常拒绝"),
                          ("repair", 7, "TCP补发"), ("summary", 5, "服务器日志")]:
    subprocess.run([ffmpeg, "-v", "error", "-y", "-ss", str(timeline[key]["start"] + offset),
                    "-i", str(video), "-frames:v", "1", "-update", "1", str(folder / (name + ".png"))], check=True)
metadata = dict(duration_seconds=duration, resolution="1280x720", video_codec="H.264", audio_codec="AAC",
                frame_rate=12, bytes=video.stat().st_size, full_decode_passed=True, narration_mean_db=mean,
                scope="真实聊天室窗口录屏，中文系统语音讲解，本机多进程真实 TCP/UDP")
(ROOT / "docs/视频验收.json").write_text(json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8")
print(json.dumps(metadata, ensure_ascii=False))
