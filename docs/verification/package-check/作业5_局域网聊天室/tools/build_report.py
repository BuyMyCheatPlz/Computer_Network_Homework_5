"""Build the submission report from the supplied template, preserving its cover.

Requires python-docx and Pillow; use the Codex bundled document runtime.
Only document.xml, its image relationships, content types and added images change.
"""
import hashlib
import io
from pathlib import Path
import re
import unicodedata
from zipfile import ZipFile, ZIP_DEFLATED

from docx import Document
from docx.enum.table import WD_CELL_VERTICAL_ALIGNMENT
from docx.enum.style import WD_STYLE_TYPE
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_BREAK, WD_LINE_SPACING
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt, RGBColor
from lxml import etree
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent.parent
DOCS = ROOT / "docs"
REFERENCE = DOCS / "参考模板.docx"
FINAL = ROOT / "局域网聊天室课程设计报告.docx"


def architecture():
    image = Image.new("RGB", (1600, 650), "white")
    draw = ImageDraw.Draw(image)
    font = ImageFont.truetype("C:/Windows/Fonts/msyh.ttc", 28)
    small = ImageFont.truetype("C:/Windows/Fonts/msyh.ttc", 24)
    def box(rect, lines):
        draw.rounded_rectangle(rect, radius=14, fill="#eef4fa", outline="#456581", width=3)
        x0, y0, x1, y1 = rect
        y = (y0 + y1) / 2 - len(lines) * 20
        for line in lines:
            draw.text(((x0+x1)/2, y), line, font=font, fill="#172f45", anchor="mt")
            y += 43
    box((70, 70, 470, 245), ["Python 客户端", "图形界面与收发线程"])
    box((70, 375, 470, 550), ["其他 Python 客户端", "在线成员与消息去重"])
    box((1080, 70, 1530, 265), ["C++17 服务端", "会话管理与任务分发"])
    box((1090, 420, 1520, 560), ["账号文件", "随机盐与 PBKDF2 摘要"])
    def arrow(a, b, color="#335c7d"):
        draw.line([a, b], fill=color, width=4)
        x, y = b
        sign = 1 if b[0] > a[0] else -1
        draw.polygon([(x, y), (x-sign*15, y-9), (x-sign*15, y+9)], fill=color)
    arrow((470, 125), (1080, 125))
    arrow((1080, 205), (470, 205))
    draw.text((775, 82), "TCP 认证  请求  ACK", font=small, fill="#172f45", anchor="mm")
    draw.text((775, 242), "TCP 成员列表  定向消息  补发", font=small, fill="#172f45", anchor="mm")
    draw.line([(1190, 265), (1190, 325), (580, 325), (580, 460)], fill="#297963", width=4)
    arrow((580, 460), (470, 460), "#297963")
    draw.line([(580, 325), (580, 285), (390, 285), (390, 245)], fill="#297963", width=4)
    draw.polygon([(390,245),(381,261),(399,261)],fill="#297963")
    draw.text((820, 360), "UDP 群聊组播 239.255.42.99:45861", font=small, fill="#21644f", anchor="mm")
    draw.line([(1300,265),(1300,420)], fill="#335c7d",width=4)
    draw.polygon([(1300,420),(1291,405),(1309,405)],fill="#335c7d")
    draw.text((1315,330), "本机持久化", font=small,fill="#172f45")
    draw.text((80,608), "TCP 45860  |  UDP TTL=1  |  SHA-256 报文校验  |  800 ms 未确认后 TCP 补发",font=small,fill="#404c55")
    image.save(DOCS / "系统结构.png")


doc = Document(REFERENCE)
if "Title" not in doc.styles:
    title_style = doc.styles.add_style("Title", WD_STYLE_TYPE.PARAGRAPH)
    title_style.font.name = "宋体"
    title_style.font.size = Pt(16)
    title_style.font.bold = True
    title_style.font.color.rgb = RGBColor(0, 0, 0)
body = doc.element.body
preserved = [etree.tostring(e, method="c14n") for e in list(body)[:23]]
for element in list(body)[23:]:
    if element.tag != qn("w:sectPr"):
        body.remove(element)


def font(run, size=12, bold=False, family="宋体"):
    run.font.name = family
    run.font.size = Pt(size)
    run.font.bold = bold
    run.font.color.rgb = RGBColor(0, 0, 0)
    fonts = run._element.get_or_add_rPr().get_or_add_rFonts()
    fonts.set(qn("w:eastAsia"), "宋体" if family == "Consolas" else family)
    return run


def paragraph(text="", size=12, bold=False, indent=True, center=False, keep=False, before=0, after=0):
    p = doc.add_paragraph()
    f = p.paragraph_format
    f.line_spacing_rule = WD_LINE_SPACING.EXACTLY
    f.line_spacing = Pt(20)
    f.space_before, f.space_after = Pt(before), Pt(after)
    f.first_line_indent = Pt(24 if indent else 0)
    f.left_indent = f.right_indent = Pt(0)
    f.keep_with_next = keep
    f.widow_control = True
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER if center else WD_ALIGN_PARAGRAPH.JUSTIFY
    font(p.add_run(text), size, bold)
    return p


def heading(text, level=1, page=False):
    p = paragraph(text, 14 if level == 1 else 12, True, indent=False, keep=True, before=8, after=5)
    outline = OxmlElement("w:outlineLvl")
    outline.set(qn("w:val"), str(level - 1))
    p._p.get_or_add_pPr().append(outline)
    if page:
        p.paragraph_format.page_break_before = True
    return p


def caption(text):
    return paragraph(text, 10.5, indent=False, center=True, keep=True, before=5, after=5)


def table(title, headers, rows, widths=None):
    caption(title)
    t = doc.add_table(rows=1, cols=len(headers))
    t.autofit = False
    widths = widths or [16 / len(headers)] * len(headers)
    for i, width in enumerate(widths):
        t.columns[i].width = Cm(width)
    for i, value in enumerate(headers):
        t.rows[0].cells[i].text = value
    repeat = OxmlElement("w:tblHeader")
    t.rows[0]._tr.get_or_add_trPr().append(repeat)
    for row in rows:
        cells = t.add_row().cells
        for i, value in enumerate(row):
            cells[i].text = str(value)
    borders = OxmlElement("w:tblBorders")
    for edge in ("top", "left", "bottom", "right", "insideH", "insideV"):
        e = OxmlElement("w:" + edge)
        e.set(qn("w:val"), "single"); e.set(qn("w:sz"), "4"); e.set(qn("w:color"), "D9D9D9")
        borders.append(e)
    t._tbl.tblPr.append(borders)
    for ri, row in enumerate(t.rows):
        no_split = OxmlElement("w:cantSplit")
        row._tr.get_or_add_trPr().append(no_split)
        for ci, cell in enumerate(row.cells):
            cell.width = Cm(widths[ci])
            cell.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER
            pr = cell._tc.get_or_add_tcPr()
            margins = OxmlElement("w:tcMar")
            for side in ("top", "left", "bottom", "right"):
                e = OxmlElement("w:" + side); e.set(qn("w:w"), "60"); e.set(qn("w:type"), "dxa"); margins.append(e)
            pr.append(margins)
            shade = OxmlElement("w:shd"); shade.set(qn("w:fill"), "E7EDF3" if ri == 0 else ("F6F8FA" if ri % 2 == 0 else "FFFFFF")); pr.append(shade)
            for p in cell.paragraphs:
                p.alignment = WD_ALIGN_PARAGRAPH.LEFT
                pf = p.paragraph_format
                pf.first_line_indent = Pt(0); pf.space_before = pf.space_after = Pt(0)
                pf.line_spacing_rule = WD_LINE_SPACING.EXACTLY; pf.line_spacing = Pt(13.5)
                for r in p.runs: font(r, 9, ri == 0)
    paragraph("", size=3, indent=False).paragraph_format.line_spacing = Pt(4)
    return t


def figure(path, label, width=15.6):
    if not path.exists():
        return
    p = paragraph(indent=False, center=True, keep=True)
    p.paragraph_format.line_spacing_rule = WD_LINE_SPACING.SINGLE
    p.add_run().add_picture(str(path), width=Cm(width))
    p = caption(label)
    p.paragraph_format.keep_with_next = False


architecture()
p = paragraph("局域网聊天室软件设计", 16, True, indent=False, center=True, keep=True, before=12, after=12)
p.style = doc.styles["Title"]
p.paragraph_format.page_break_before = True
paragraph("选题编号 5    Python 客户端与 C++ 服务端", 12, indent=False, center=True, after=10)
heading("一 选题背景")
paragraph("本课题面向同一局域网中的多人文字交流，设计并实现具有注册、登录、注销、成员列表、群发和选定多人发送能力的聊天室。系统采用客户机与服务器模式，以 UDP 组播承担群聊下行，以 TCP 承担账号控制和定向消息，并在应用协议中设置明确的任务码、错误语义和完整性校验结构。")
paragraph("设计目标是让通信功能、协议约束和可验证的实现相互对应。程序不仅应在正常输入下完成中文交流，还应能处理不存在的任务码、错误参数、篡改报文、TCP 拆包粘包和连接中断。交付内容包括可运行程序、完整项目源码、协议说明、真实测试记录和带讲解的运行录像。")
table("表1 作业要求与实现映射", ["要求", "实现位置与行为"], [
    ("局域网多人通信", "服务端向 239.255.42.99:45861 发送 UDP 组播，TTL 为 1"),
    ("客户机与服务器模式", "Python Tkinter 客户端与 C++17 Winsock 服务端"),
    ("中英文文本", "UTF-8 JSON，支持中文账号、中文英文正文和换行"),
    ("账号与界面", "注册、登录、注销、在线名单、会话记录和输入框"),
    ("群发和指定多人", "群发按钮；名单多选后 TCP 定向，仅目标与发送者接收"),
    ("无效任务与完整性", "INVALID_TASK 等错误响应；SHA-256 校验失败则不执行业务"),
    ("报告与录像", "详细语法语义设计、源码附录、测试证据和 720p MP4")], [4, 11.7])

heading("二 方案论证", page=True)
heading("2 1 通信方式与语言分工", 2)
paragraph("若全部采用 TCP 单播，群发时服务端需要逐连接重复传输正文；若全部采用 UDP，账号认证、定向隔离和可靠交付均需另外实现。结合课程对组播或广播的要求，本方案采用 TCP 控制通道与 UDP 组播群聊的组合。IPv4 组播把一个数据报发送给加入同一组的接收者，天然适合多人群发，但并不保证交付和到达顺序[1]。")
paragraph("Python 负责窗口、用户操作、协议封装和收包事件分发，聊天程序运行只依赖标准库。C++17 负责连接接入、账号校验、成员状态、组播发送和补发队列，使用 Windows Winsock 与 BCrypt。两端通过相同的 UTF-8 报文结构和摘要规则互通，避免依赖同一种语言的对象布局。")
heading("2 2 可靠性与安全边界", 2)
paragraph("服务端对群聊保存每位在线成员的待确认项。客户端成功验包后回送 ACK；约 800 毫秒仍未确认时，服务端通过原 TCP 会话补发一次。客户端记录最近 2048 个消息标识，UDP 副本和 TCP 副本只展示一次。补发依赖仍然在线的 TCP 连接，不提供离线队列或跨重启聊天历史。")
paragraph("账号文件不存明文密码，而是保存 16 字节随机盐和 200000 次迭代的 PBKDF2-HMAC-SHA256 派生摘要，派生长度为 32 字节[2]。报文使用 SHA-256 检出内容改变。未采用 TLS 或带密钥的消息认证码，因此不能阻止攻击者修改内容后重新计算摘要；密码在传输链路中仍为明文。本设计的安全结论仅限课程局域网演示环境。")
heading("2 3 运行环境与部署约束", 2)
paragraph("实测环境为 Windows、Python 3.14.7、MinGW-w64 GCC 16.1.0。客户端要求 Python 3.10 以上并安装 Tcl/Tk；已提供静态链接的 C++ 服务端可执行文件。默认 TCP 端口为 45860，UDP 端口为 45861，每连接最多受理 120 请求每秒，最多保持 64 条 TCP 连接，每条正文最多 2000 个 Unicode 码点。该连接上限属于实现约束，不代表已完成 64 人并发性能验证。")
paragraph("两台电脑联机时均接入同一局域网。客户端服务器地址填写服务端电脑的局域网 IPv4，多网卡机器指定实际组播网卡。系统需允许对应 TCP 和 UDP 端口通信。校园网 AP 隔离、交换机策略或跨网段部署可能阻止组播；此时群聊仍可经 TCP 补发到达，但该现象不能当作跨机组播验收通过。")

heading("三 过程论述", page=True)
heading("3 1 模块结构与数据流", 2)
paragraph("为说明账号控制、定向消息和群聊共享同一会话状态但采用不同传输路径，图1给出模块及数据流。客户端主线程负责界面，网络线程通过事件队列向主线程传递收包结果，符合 Tkinter 的事件与线程使用方式[3]。")
figure(DOCS / "系统结构.png", "图1 聊天室模块结构与传输路径")
paragraph("图中客户端向服务端发送注册、登录和聊天请求，服务端取得连接绑定的真实用户名，完成参数校验后分发消息。群聊下行进入组播组，定向消息只写入目标成员及发送者的 TCP 连接；账号存储仅在服务端本机访问。客户端每 4 秒发送心跳，服务端读超时为 15 秒、写超时为 5 秒。")
table("表2 工程模块与职责", ["文件", "职责"], [
    ("server_cpp/main.cpp", "C++ 帧解析、任务分发、账号持久化、成员管理、组播与补发"),
    ("lan_chat/protocol.py", "跨语言统一的报文格式、序列化、摘要、TCP 帧读取"),
    ("lan_chat/client.py", "TCP 连接、UDP 入组、ACK、去重与心跳"),
    ("lan_chat/gui.py", "账号界面、聊天输入、多人选择、状态和日志显示"),
    ("lan_chat/native_server.py", "启动和监控 C++ 服务进程，管理退出与日志"),
    ("tests/test_chat.py", "启动真实 C++ 进程并验证 TCP 和 UDP 行为")], [5.2, 10.5])
heading("3 2 账号与会话状态", 2)
paragraph("未登录连接可以注册、登录或发送心跳；注册成功不会自动登录。登录成功后，用户名与当前连接绑定，并加入在线表。同一用户名不能同时登录两条连接。注销只移除在线会话及其待确认消息，不删除账号。读到 EOF、网络错误或读超时后，服务端清理成员并推送新名单。")
paragraph("注册时先校验用户名和密码范围，再生成随机盐并派生摘要，将新账号写入临时文件，刷新后原子替换账号文件。账号访问加锁，避免并发注册覆盖；每个连接写入加锁，避免多个线程交错写入导致帧损坏。成员名单推送串行化，防止旧快照在新快照之后到达。")

heading("3 3 应用协议语法", 2)
paragraph("协议名为 LCP 1。TCP 帧由 4 字节大端无符号长度 N 和 N 字节 UTF-8 JSON 组成，N 的有效范围为 1 至 32768。接收函数先循环读满 4 字节，再循环读满正文，因此可以处理拆包和粘包。UDP 一个数据报恰好携带一份 JSON，不含 TCP 长度前缀。")
table("表3 报文顶层字段", ["字段", "语法约束", "语义"], [
    ("v", "整数 1", "协议版本，不接受布尔值"),
    ("id", "32 位小写十六进制字符串", "独立随机报文标识"),
    ("type", "1 至 40 字节字符串", "区分大小写的任务码"),
    ("ts", "0 至 2^53-1 的整数", "Unix 毫秒时间戳，用于展示"),
    ("body", "JSON 对象", "具体任务参数"),
    ("checksum", "64 位小写十六进制字符串", "其余五字段的 SHA-256 摘要")], [2.5, 6.1, 7.1])
paragraph("顶层只允许表3列出的六个字段，缺失、额外字段、重复键、非法 UTF-8 和不支持的版本均拒绝。JSON 键递归排序，使用紧凑分隔符，不转义中文；业务字段不使用浮点数。C++ 解析器还限制嵌套深度，避免过深对象占用调用栈。")
heading("3 4 客户端任务语义", 2)
table("表4 客户端请求与状态约束", ["任务", "body 主要字段", "语义与前置状态"], [
    ("REGISTER", "name, password", "未登录；用户名 1 至 20 个汉字或 ASCII 字母数字及 _ -；密码 6 至 128 字符"),
    ("LOGIN", "name, password", "未登录；校验密码并检查账号未在线；成功返回组播配置"),
    ("LOGOUT", "空对象", "已登录；退出会话，保留注册账号"),
    ("MEMBERS", "空对象", "已登录；触发完整成员名单推送"),
    ("CHAT", "text, mode=all, targets=[]", "已登录；群发给当前所有在线成员，包含发送者"),
    ("CHAT", "text, mode=selected, targets", "已登录；目标 1 至 64 人且全部在线；TCP 定向，回显给发送者"),
    ("ACK", "message_id", "已登录；清除该用户的一条群聊待确认项"),
    ("PING", "空对象", "任意连接状态；返回 PONG，保持连接活跃")], [2.9, 5.3, 7.5])
paragraph("CHAT 正文要求 1 至 2000 个 Unicode 码点且不能全为空白。定向目标去重，任一目标离线则整条拒绝，避免部分成员收到而发送方误判。发送者以已登录连接为准，不能由请求体伪造。每连接保留最近 512 个合法任务请求 id，重复时返回 REPLAY；该策略是有界的会话内去重，不属于跨连接防重放。")
heading("3 5 服务端响应与错误处理", 2)
table("表5 服务端响应字段与业务含义", ["响应", "主要字段与含义"], [
    ("RESULT", "request 关联原请求，action 标识任务，ok 表示成功或失败，message 为提示"),
    ("登录 RESULT", "附加 name、group、udp_port、room_id，用于加入服务实例对应的聊天室"),
    ("聊天 RESULT", "附加 message_id，只表示服务端受理，不等于所有成员已展示"),
    ("ROSTER", "members 为排序后的完整名单，客户端替换旧名单"),
    ("MESSAGE", "room_id、sender、text、mode、targets、recipients、request；外层 id 用于 ACK 和去重"),
    ("ERROR", "code、message、request；无法解析原 id 时 request 为空串"),
    ("PONG", "request 关联心跳请求")], [3.3, 12.4])
table("表6 典型错误语义与恢复方式", ["代码", "条件", "处理"], [
    ("INVALID_TASK", "不存在的任务码", "返回错误，保持连接"),
    ("BAD_PACKET", "JSON、UTF-8、字段、版本错误", "丢弃当前已知边界的帧，继续读取"),
    ("BAD_CHECKSUM", "摘要不匹配", "不执行业务，连接保留"),
    ("FRAME_TOO_LARGE", "长度 0 或超过 32768", "返回错误并关闭该输入连接"),
    ("BAD_BODY", "类型或字符数不合法", "拒绝当前任务"),
    ("AUTH_FAILED", "用户名不存在或密码错误", "保持未登录"),
    ("ALREADY_ONLINE", "账号已在另一连接登录", "拒绝重复登录"),
    ("NOT_LOGGED_IN", "未登录执行聊天等任务", "拒绝执行业务"),
    ("STATE", "在线状态再次注册或登录", "要求先注销"),
    ("NO_RECIPIENT", "目标为空或包含离线账号", "整条定向消息不发送"),
    ("REPLAY", "本连接近期请求 id 重复", "不重复执行业务"),
    ("RATE_LIMIT", "每秒超过 120 请求", "拒绝当前请求")], [4.2, 5.3, 6.2])

heading("3 6 完整性校验结构与算法", 2)
paragraph("发送方构造 v、id、type、ts、body 五字段对象，递归按键名排序，以无多余空白的 UTF-8 JSON 编码得到字节串 M，计算 SHA-256(M)，将结果转为 64 位小写十六进制字符串并填入 checksum。接收方重新执行相同计算，用等长逐字节方式比较摘要。")
paragraph("处理顺序为：帧长度检查、UTF-8 与 JSON 解析、字段约束检查、摘要验证、任务码检查、会话与参数检查、执行业务。修改 body.text 而保留旧摘要，会返回 BAD_CHECKSUM；构造校验正确但 type 不存在的报文，会返回 INVALID_TASK。两类错误分别覆盖语法完整性和无效语义，均不使服务器退出。")
heading("3 7 组播确认与补发流程", 2)
paragraph("群发受理时，服务端取得在线成员快照，为每位成员创建以用户名和 MESSAGE.id 为键的待确认记录，截止时间为当前单调时钟加 800 毫秒，然后发送一次 UDP 组播。客户端校验房间实例和实际收件名单后回 ACK，再通过最近消息 id 集合去重展示。")
paragraph("后台补发线程每 100 毫秒检查一次截止时间；超过截止时间仍未确认且该成员在线时，经其 TCP 连接发送原报文并删除记录。由于扫描间隔和调度影响，约 0.8 至 0.9 秒后触发补发，不构成实时性能保证。组播 ACK 丢失时可能出现重复副本，客户端只展示一次。超出链路 MTU 的 UDP 报文可能被 IP 分片，任何分片丢失均可能使该消息走 TCP 补发。")

heading("3 8 图形界面与实际运行", 2, page=True)
paragraph("界面将账号操作、会话、成员和消息输入放在同一页。图2展示已登录状态及中文消息，图3用独立客户端实际收包记录验证两人定向发送和旁观者隔离。界面网络操作在后台线程执行，主线程以定时轮询事件队列更新控件；连接重试使用代次标识忽略旧连接遗留事件。")
figure(DOCS / "screenshots/群聊.png", "图2 中文群聊与在线成员界面")
figure(DOCS / "screenshots/定向隔离.png", "图3 两位目标与旁观者的实际接收记录")
paragraph("图2的传输标记用于区分 UDP 组播和 TCP 补发，不能仅凭消息到达就断定组播成功。图3中小周与小陈收到定向正文，旁听同学只保留群聊记录。服务器管理页显示实际 C++ 子进程输出，便于核对组播、定向、错误拒绝和补发行为。")

heading("四 结果分析", page=True)
heading("4 1 测试方法与实测结果", 2)
paragraph("自动测试真实启动编译后的 C++ 服务进程，再通过 Python 客户端建立 TCP 和 UDP 连接；账号文件使用临时目录，测试结束停止进程并清理。当前 12 项测试全部通过，原始输出保存在 docs/测试结果.txt。该结果来自本机真实网络栈、多线程和多进程运行，没有把模拟收包当作实测。")
table("表7 自动测试覆盖与结果", ["编号", "测试内容", "结果"], [
    ("01", "中英文、表情和换行报文编解码", "通过"),
    ("02", "正文被修改而摘要不变，检出篡改", "通过"),
    ("03", "JSON、UTF-8、重复键、非有限数与超长报文拒绝", "通过"),
    ("04", "注册登录、错误密码、重复账号、重复在线及派生摘要互验", "通过"),
    ("05", "两客户端真实 UDP 中文组播与相同 id 去重", "通过"),
    ("06", "选中两人接收，第四个账号不接收定向消息", "通过"),
    ("07", "关闭一客户端组播后，约 800 ms 经 TCP 补发", "通过"),
    ("08", "不存在任务码及错误摘要后继续正常响应心跳", "通过"),
    ("09", "两帧粘连、每次 7 字节拆分发送仍能准确解帧", "通过"),
    ("10", "恶意格式、匿名聊天、超大帧；新连接仍正常", "通过"),
    ("11", "空白与超长正文、目标错误、重复请求、离线名单", "通过"),
    ("12", "服务端重启后仍能读取已注册账号登录", "通过")], [1.6, 12.5, 1.6])
heading("4 2 演示结果与工程解释", 2)
paragraph("演示录像使用一个 C++ 服务端、主窗口客户端和三个独立网络客户端。群聊被全部在线成员接收；定向正文只在小周与小陈的接收列出现，旁听同学未收到。将旁听同学退出组播组后仍保留 TCP 会话，再次群发时该客户端通过 TCP 收到补发。录像记录为真实 GUI 画面，中文讲解为系统语音合成。")
figure(DOCS / "screenshots/异常拒绝.png", "图4 无效任务与完整性错误被拒绝后继续通信")
paragraph("组播降低了正常群发下行重复发送正文的次数，但仍需每位成员回 ACK，服务端也维护按成员数量增长的待确认状态。因此本实现是面向小规模课程聊天室的方案，没有据此宣称具备互联网规模吞吐能力。多线程和连接写锁保障帧不交错，不能保证所有客户端按照同一全局顺序看到并发群聊。")
heading("4 3 未验证范围与现场验收", 2)
paragraph("本次未在两台实体电脑之间完成验收，也未开展 64 人负载、校园 AP 丢包率、实际链路吞吐和长期运行测试。现场应在两台同网段电脑分别启动客户端，确认成员名单、双向中文群聊、两人定向隔离和注销同步，并在日志中看到 UDP 组播标记。如果仅出现 TCP 标记，只能证明可靠回退生效，不能代替跨机组播验证。")

heading("五 课程设计总结")
paragraph("本设计把面向连接的控制通道与无连接的组播通道组合，实现了账号会话、多人群聊和定向发送。协议实现从字节边界、语法、完整性和语义四个层次逐步校验，使异常任务与受损报文能被明确拒绝。跨语言互通的关键在于约定规范化 JSON、整型毫秒时间戳、UTF-8 编码和统一摘要范围，而不能依赖语言默认对象表示。")
paragraph("实现过程中需要关注 Windows 多网卡组播选择、TCP 分段、异步界面更新和资源退出。自动测试和录像提供了可重复的正常与异常证据；后续可增加 TLS、消息认证、持久化历史、重新连接、服务器发现以及跨机器网络测试。引入这些能力时应同步更新协议版本与测试，避免仅增加界面按钮而缺少一致的服务端语义。")

doc.paragraphs[-1].paragraph_format.keep_together = True
heading("参考文献")
for text in [
    "[1] Deering S. Host Extensions for IP Multicasting. RFC 1112, 1989, 第2至3节. https://www.rfc-editor.org/rfc/rfc1112.txt. 访问日期 2026-10-31.",
    "[2] Moriarty K, Kaliski B, Rusch A. PKCS #5 Password-Based Cryptography Specification Version 2.1. RFC 8018, 2017, 第5.2节. https://www.rfc-editor.org/rfc/rfc8018.txt. 访问日期 2026-10-31.",
    "[3] Python Software Foundation. tkinter Python interface to Tcl/Tk, Threading model. https://docs.python.org/3/library/tkinter.html. 访问日期 2026-10-31.",
    "[4] Lohmann N. JSON for Modern C++, version 3.11.3. https://github.com/nlohmann/json/tree/v3.11.3. MIT License. 访问日期 2026-10-31."]:
    paragraph(text, 10.5, indent=False)

heading("附录 A 核心程序完整源码", page=True)
paragraph("以下按文件列出本课题核心自编源码，行号对应交付工程。过长行在排版时折行，续行以 > 标识；可执行源码以工程文件为准。第三方 nlohmann/json 3.11.3 头文件体量较大，随 server_cpp/vendor/json.hpp 与 MIT 许可证独立提交，不重复印入本附录。自动测试完整源码另见附录 B。", 10.5)


def wrapped_line(text, limit=100):
    result, current, count = [], "", 0
    for char in text.expandtabs(4):
        size = 2 if unicodedata.east_asian_width(char) in ("W", "F") else 1
        if count + size > limit:
            result.append(current); current = ""; count = 0
        current += char; count += size
    result.append(current)
    return result


def listing(relative, page=True):
    heading(relative, 2, page)
    lines = []
    for number, line in enumerate((ROOT / relative).read_text(encoding="utf-8").splitlines(), 1):
        wrapped = wrapped_line(line, 99)
        lines.append(f"{number:4}  {wrapped[0]}")
        lines.extend("   >  " + part for part in wrapped[1:])
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.LEFT
    pf = p.paragraph_format
    pf.first_line_indent = pf.left_indent = pf.right_indent = Pt(0)
    pf.space_before = pf.space_after = Pt(0)
    pf.line_spacing_rule = WD_LINE_SPACING.EXACTLY
    pf.line_spacing = Pt(10)
    pf.widow_control = False
    font(p.add_run("\n".join(lines)), 7.5, family="Consolas")


for i, file in enumerate(["server_cpp/main.cpp", "lan_chat/protocol.py", "lan_chat/client.py", "lan_chat/gui.py", "lan_chat/native_server.py"]):
    listing(file, page=i != 0)
heading("启动与构建文件", 2, page=True)
for file in ["lan_chat/__init__.py", "lan_chat/__main__.py", "start.bat", "start_server.bat", "build_server.bat"]:
    listing(file, page=False)
heading("附录 B 自动测试完整源码", page=True)
listing("tests/test_chat.py", page=False)

# Preserve all existing package parts except explicit body/image edits.
buffer = io.BytesIO()
doc.save(buffer)
buffer.seek(0)
with ZipFile(REFERENCE) as source, ZipFile(buffer) as edited, ZipFile(FINAL, "w", ZIP_DEFLATED) as output:
    allowed = {"word/document.xml", "word/_rels/document.xml.rels", "[Content_Types].xml", "word/styles.xml"}
    for item in source.infolist():
        output.writestr(item, edited.read(item.filename) if item.filename in allowed else source.read(item.filename))
    for item in edited.infolist():
        if item.filename not in source.namelist():
            assert item.filename.startswith("word/media/"), item.filename
            output.writestr(item, edited.read(item.filename))
    unchanged = [n for n in source.namelist() if n not in allowed]

with ZipFile(REFERENCE) as source, ZipFile(FINAL) as final:
    root = etree.fromstring(final.read("word/document.xml"))
    final_body = root.find(qn("w:body"))
    assert [etree.tostring(e, method="c14n") for e in list(final_body)[:23]] == preserved, "Cover or review page changed"
    assert all(source.read(n) == final.read(n) for n in unchanged)
    evidence = dict(original_doc_sha256=hashlib.sha256((ROOT / "课程设计报告书-模版(1).doc").read_bytes()).hexdigest(),
                    cover_elements_unchanged=23, immutable_parts_identical=len(unchanged),
                    changed_existing_parts=sorted(allowed), source_files_in_appendix=11)
    import json
    (DOCS / "模板结构验证.json").write_text(json.dumps(evidence, ensure_ascii=False, indent=2), encoding="utf-8")
print(FINAL)
