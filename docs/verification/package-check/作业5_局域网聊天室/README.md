# 作业 5 局域网聊天室

Python 3.10+ 图形客户端 + C++17 Windows 服务端。群聊使用真实 IPv4 UDP 组播，定向消息经 TCP 发给所选多人，账号持久保存，报文使用 SHA-256 校验。提供源代码、已编译服务端、模板报告、测试和演示录像。

## 快速开始

1. 安装带 Tkinter 的 Python 3.10+（本机测试版本 3.14.7）。已有 `bin/chat_server.exe`，运行时无需 C++ 编译器、pip 或第三方 Python 包。
2. 双击 `start.bat`，或在本目录运行 `python -m lan_chat`。
3. 在“服务器管理”页启动服务器。单机演示保持默认配置。
4. 回到“聊天室”，填写用户名和至少 6 位密码，先注册，再登录。
5. 再打开两个以上客户端窗口，分别注册其他账号。点击“群发”发送中文；单击成员列表可多选，点击“发送给选中成员”定向发送。
6. “注销”退出当前登录，账号仍保留。关闭窗口自动断开；启动服务的窗口关闭时同时停止其 C++ 服务端。

若双击闪退，请在 PowerShell 中运行 `python -m lan_chat` 查看提示。Python Windows 安装器需勾选 Tcl/Tk 支持；`python -m tkinter` 可检查环境。

## 两台或多台电脑联机

- 所有电脑连接同一局域网。在服务器电脑用 `ipconfig` 查找正在使用的 Wi-Fi 或以太网 IPv4，例如 192.168.1.20。
- 服务器监听地址保持 0.0.0.0；有多个网卡或 VPN 时，将“组播出口 IPv4”填写为该局域网网卡地址。
- 其他电脑的客户端将“服务器 IPv4”改为服务器地址。客户端“本机组播 IPv4”填写本机同一局域网网卡地址；单网卡通常可保持 0.0.0.0。
- 联机需要系统允许 Python 接收 UDP 45861、允许服务端接收 TCP 45860。按学校网络和系统提示授权对应程序，无需关闭防火墙。
- 若校园 AP 隔离客户端、禁用组播或跨网段，组播可能不通；群聊会约 0.8 秒后经 TCP 补发。记录中显示“UDP 组播”才证明当次走组播，显示“TCP”说明使用可靠通道。
- 当前证据为本机多进程真实 TCP/UDP 实测；提交前应在两台实体电脑按上述步骤验收并记录。

也可独立启动服务端：

```powershell
.\bin\chat_server.exe --host 0.0.0.0 --port 45860 --interface 192.168.1.20 --db data/accounts.json
```

服务器只运行一个实例。终端中 Ctrl+C 停止服务；GUI 服务器管理页只管理由该窗口启动的服务进程。

## 编译与测试

双击 `build_server.bat`，需要 MinGW-w64 的 g++ 在 PATH 中。命令：

```powershell
g++ -std=c++17 -municode -O2 -Wall -Wextra -finput-charset=UTF-8 -fexec-charset=UTF-8 -static -static-libgcc -static-libstdc++ server_cpp/main.cpp -o bin/chat_server.exe -lws2_32 -lbcrypt
python -m unittest -v tests.test_chat
```

MSVC 开发者命令行可运行：

```bat
cl /std:c++17 /EHsc /utf-8 server_cpp\main.cpp /Fe:bin\chat_server.exe ws2_32.lib bcrypt.lib
```

实际编译已验证 MinGW-w64 GCC 16.1.0，MSVC 命令供对应环境使用，未在本机实测。

`data/accounts.json` 含用户名、16 字节随机盐、PBKDF2-HMAC-SHA256 派生摘要（200000 次迭代），不存明文密码。注册时原子替换持久化文件。不要混用演示账号文件和正式账号文件。

## 对应作业条目

| 作业要求 | 实现与证据 |
|---|---|
| 局域网多人通信，组播或广播 | 239.255.42.99:45861 UDP 组播，TTL=1；带 ACK 与 TCP 补发 |
| 客户机与服务器模式 | Python TCP/UDP 客户端，C++ Winsock 服务端 |
| 中英文文本 | UTF-8 JSON；中文账号和中文、英文、换行消息 |
| 注册、登录、注销、成员、对话框 | 图形界面及账号文件，成员实时推送 |
| 群发及选定多人 | 群发按钮；在线名单多选后 TCP 定向，未选中成员不接收 |
| 无效语义与不存在任务码 | INVALID_TASK、BAD_BODY、NOT_LOGGED_IN 等稳定错误码 |
| 报文完整性结构与算法 | 五字段规范化 JSON + SHA-256，校验失败拒绝执行 |
| 协议语法和语义说明 | `docs/协议设计.md` 与实践报告正文 |
| 源代码附录 | 报告附录及 `server_cpp/`、`lan_chat/`、`tests/` |
| 录像和提交包 | `演示视频.mp4`、RAR 提交包及验收记录 |

## 目录

`server_cpp/main.cpp` 为服务端；`server_cpp/vendor/` 为固定版本 nlohmann/json 3.11.3 与 MIT 许可证。`lan_chat/` 为 Python 客户端、协议及 GUI。`tests/` 为真实网络集成测试。`docs/` 含协议、报告与测试证据。`tools/` 为报告生成、演示和打包工具。

本实现适合课程演示。SHA-256 摘要可检出不重新计算摘要的内容修改，不具备发送者认证；当前没有 TLS/HMAC，通信链路未加密。定向发送通过 TCP 控制接收范围，但不等于端到端保密。无离线消息和历史记录持久化，不保证组播全局顺序。GUI 本身只依赖 Python 标准库；报告与视频工具的依赖不属于聊天程序运行要求。

## 重录与重新生成材料

重录需要 Windows 桌面保持解锁、系统中文语音，以及 FFmpeg。使用 `python -m pip install --target tools/media_runtime imageio-ffmpeg==0.6.0` 安装录屏依赖，运行 `tools/make_narration.ps1` 生成讲解，再运行 `python tools/demo.py`。脚本只录制演示程序窗口，实际运行一个 C++ 服务端与四条客户端连接，完成后自动核对组播、定向隔离和 TCP 补发；演示账号保存在临时目录，不影响正式账号。可选媒体运行包体积较大，未纳入提交 RAR。

报告生成需 `python-docx` 和 `Pillow`，运行 `python tools/build_report.py`；该脚本从 `docs/参考模板.docx` 保留封面与教师评语页，正文截图来自演示视频。重新生成时先用 Word 从原始 DOC 另存得到参考模板。最终报告另在 Word 中导出 PDF。提交包脚本 `python tools/package_submission.py` 写入标准 RAR5 存储归档，支持 UTF-8 文件名与 CRC32 校验，可用 WinRAR 或 7-Zip 打开。

按题目截图，截止时间为 **2026-11-20 23:59**；视频要求 3 分钟以内、720p、MP4；最终 RAR 不超过 100MB。按用户要求，报告封面保留模板原有信息。
