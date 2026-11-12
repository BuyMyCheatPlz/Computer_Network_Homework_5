"""Write a genuine RAR 5 archive using the documented Store method.

No renamed ZIP and no external archiver needed. Files carry CRC32 checksums.
Format: https://www.rarlab.com/technote.htm . Validate with 7z t output.rar.
"""
import hashlib
import json
from pathlib import Path
import struct
import zlib

ROOT = Path(__file__).resolve().parent.parent
OUTPUT = ROOT / "作业5_局域网聊天室_提交包.rar"


def vint(number):
    data = bytearray()
    while number >= 128:
        data.append((number & 127) | 128)
        number >>= 7
    data.append(number)
    return bytes(data)


def header(data):
    block = vint(len(data)) + data
    return struct.pack("<I", zlib.crc32(block)) + block


def selected_files():
    single = ["README.md", "THIRD_PARTY_NOTICES.md", "start.bat", "start_server.bat", "build_server.bat", ".gitignore",
              "局域网聊天室课程设计报告.docx", "局域网聊天室课程设计报告.pdf",
              "演示视频.mp4", "演示字幕.srt", "提交前检查.md", "课程设计报告书-模版(1).doc"]
    trees = ["lan_chat", "server_cpp", "tests", "bin"]
    files = [ROOT / name for name in single]
    for tree in trees:
        files.extend(path for path in (ROOT / tree).rglob("*") if path.is_file() and "__pycache__" not in path.parts)
    for name in ["参考模板.docx", "参考模板.pdf", "artifact.md", "协议设计.md", "测试结果.txt", "模板保留说明.md", "模板结构验证.json", "封面像素验证.json",
                 "演示实测记录.json", "演示时间轴.json", "视频验收.json", "系统结构.png"]:
        files.append(ROOT / "docs" / name)
    files.extend((ROOT / "docs/screenshots").glob("*.png"))
    # Reproduction tools are included; bulky media runtime is optional, excluded.
    for name in ["build_report.py", "demo.py", "demo_segments.json", "make_narration.ps1", "package_submission.py", "verify_media.py", "verify_report.py"]:
        files.append(ROOT / "tools" / name)
    for file in files:
        if not file.is_file():
            raise FileNotFoundError(file)
    return sorted(set(files))


def main():
    files = selected_files()
    manifest = []
    with OUTPUT.open("wb") as out:
        out.write(b"Rar!\x1a\x07\x01\x00")
        out.write(header(vint(1) + vint(0) + vint(0)))
        for file in files:
            data = file.read_bytes()
            relative = "作业5_局域网聊天室/" + file.relative_to(ROOT).as_posix()
            name = relative.encode("utf-8")
            # Type 2, common flag DATA_PRESENT=2, file flag CRC_PRESENT=4.
            fields = (vint(2) + vint(2) + vint(len(data)) + vint(4) + vint(len(data)) +
                      vint(0x20) + struct.pack("<I", zlib.crc32(data)) + vint(0) +
                      vint(0) + vint(len(name)) + name)
            out.write(header(fields))
            out.write(data)
            manifest.append(dict(path=relative, bytes=len(data), sha256=hashlib.sha256(data).hexdigest()))
        out.write(header(vint(5) + vint(0) + vint(0)))
    size = OUTPUT.stat().st_size
    assert size < 100_000_000, f"Archive exceeds 100 MB: {size}"
    (ROOT / "docs/提交包清单.json").write_text(json.dumps(dict(archive=OUTPUT.name, bytes=size,
            method="RAR5 Store", files=manifest), ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"RAR5: {len(files)} files, {size/1_000_000:.2f} MB -> {OUTPUT}")


if __name__ == "__main__":
    main()
