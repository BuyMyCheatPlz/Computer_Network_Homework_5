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
    box((1090, 420, 1520, 560), ["账号持久化文件", "PBKDF2 加盐安全散列"])
    def arrow(a, b, color="#335c7d"):
        draw.line([a, b], fill=color, width=4)
        x, y = b
        sign = 1 if b[0] > a[0] else -1
        draw.polygon([(x, y), (x-sign*15, y-9), (x-sign*15, y+9)], fill=color)
    arrow((470, 125), (1080, 125))
    arrow((1080, 205), (470, 205))
    draw.text((775, 82), "TCP 可靠通道：注册 / 登录 / 心跳 / ACK 确认", font=small, fill="#172f45", anchor="mm")
    draw.text((775, 242), "TCP 可靠通道：成员列表同步 / 定向私聊 / 超时补发", font=small, fill="#172f45", anchor="mm")
    draw.line([(1190, 265), (1190, 325), (580, 325), (580, 460)], fill="#297963", width=4)
    arrow((580, 460), (470, 460), "#297963")
    draw.line([(580, 325), (580, 285), (390, 285), (390, 245)], fill="#297963", width=4)
    draw.polygon([(390,245),(381,261),(399,261)],fill="#297963")
    draw.text((820, 360), "UDP 组播通道：239.255.42.99:45861 (TTL=1)", font=small, fill="#21644f", anchor="mm")
    draw.line([(1300,265),(1300,420)], fill="#335c7d",width=4)
    draw.polygon([(1300,420),(1291,405),(1309,405)],fill="#335c7d")
    draw.text((1315,330), "本地磁盘安全持久化", font=small,fill="#172f45")
    draw.text((80,608), "网络配置：TCP 45860 | UDP TTL=1 局域网控制 | SHA-256 完整性防篡改 | ACK + 800ms 超时 TCP 补发",font=small,fill="#404c55")
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
paragraph("局域网多人即时通信（Instant Messaging）是计算机网络中最典型、最综合的应用场景之一，涵盖客户机/服务器（C/S）体系结构、传输层协议特性（TCP 与 UDP）、IP 组播技术、应用层通信协议设计、报文定界与数据完整性校验等核心知识点。本课题面向局域网内部多人文本交互需求，设计并实现了一套具备账号注册、登录认证、注销退出、实时在线列表同步、多人群发以及选定多人精准定向发送（私聊）能力的局域网聊天室系统。")
paragraph("系统采用跨语言协同架构，由 Python 3 图形客户端与 C++17 高性能服务端协同构建。群聊采用高效的 IPv4 组播（Multicast）技术，用户认证与定向私聊采用高可靠的 TCP 单播，并在应用层实现了 4 字节大端长度前缀定界（解决 TCP 粘包拆包问题）、基于 SHA-256 的报文完整性校验、应用层 ACK 确认与超时重传（实现网络抖动环境下的可靠传输保证），以及基于 PBKDF2 的加盐密码安全存储机制。系统既有扎实的网络原理支撑，又具备完整的工程交付成果，包括可运行软件、全套源代码、详细协议设计、12 项自动化网络集成测试及演示录像。")

table("表1 作业要求与实现映射", ["要求", "实现位置与行为"], [
    ("局域网多人通信", "服务端向 239.255.42.99:45861 发送 UDP 组播，TTL=1；带应用层 ACK 与 TCP 补发"),
    ("客户机与服务器模式", "Python Tkinter 图形客户端与 C++17 Winsock2 高性能服务端"),
    ("中英文文本支持", "UTF-8 JSON 编码传输，支持中文账号、中英文正文及多行换行消息"),
    ("账号与界面交互", "图形化注册、登录、注销、在线成员列表动态刷新、聊天记录展示与输入框"),
    ("群发与选定多人私聊", "群发按钮走组播；列表多选好友后走 TCP 定向单播，未选中成员完全隔离"),
    ("无效任务码与容错处理", "应用层完备状态机，遇到无效任务码或错误参数返回统一错误响应且不崩溃"),
    ("报文完整性防篡改", "五字段标准化序列化 + SHA-256 散列校验，单比特变动即拒绝执行业务"),
    ("规范技术文档与交付物", "详细协议设计规范、核心源码附录、自动化测试证据及 720p 演示视频")], [4, 11.7])

heading("二 方案论证", page=True)
heading("2 1 通信方式选型与传输原理", 2)
paragraph("在网络协议选型上，如果群聊全部采用 TCP 单播，当群内有 N 位在线成员时，服务端转发一条群聊消息就必须在 N 条独立的 TCP 连接上分别复制、序列化并发送该数据包 N 次。随着在线人数增加，服务端 CPU 和出口带宽将随人数呈线性增长，容易造成服务器计算压力与局域网网络拥塞。相反，若全部采用 UDP，虽然协议开销低、并发能力强，但 UDP 作为轻量无连接协议，设计目标偏向传输效率而非连接状态维护。在用户注册认证、登录握手与在线成员动态同步等关键业务中，强一致性的时序保证至关重要；同时在定向私聊场景中，TCP 单播能够在传输链路层面天然实现点对点的私密隔离。因此，将面向连接的 TCP 与无连接的 UDP 有机结合，构建双通道互补模型，是兼顾传输性能与业务可靠性的最优方案。")
paragraph("本系统设计的“TCP 控制通道 + UDP 组播群聊”双通道混合传输架构充分发挥了二者的技术优势。IPv4 组播利用 Class D 类特殊地址（本项目使用 239.255.42.99:45861）。服务端转发群发消息时，只需向该地址发送一次数据报，底层交换机与网卡硬件会根据 IGMP 协议自动识别组播成员，在硬件链路层高效复制并分发给所有加入了该组播组的主机，极大地节约了网络带宽资源[1]。而在账号注册、登录认证、在线成员同步以及定向私聊时，则采用面向连接、提供可靠顺序交付的 TCP 协议（端口 45860）。定向私聊通过 TCP 单播仅发送给被选中的客户端 Socket，未被选中的第三方用户在物理网络链路上根本不会收到该数据包，实现了底层网络级别的隐私隔离。")
paragraph("在软件实现分工上，Python 客户端依托内置 Tkinter 快速构建直观友好的图形交互界面，网络通信线程与界面主线程解耦，避免网络阻塞界面；C++17 服务端依托 Windows 原生 Winsock2 API 与多线程，负责高并发网络 I/O 调度、会话认证、组播下发与重传队列管理。两侧遵循统一的规范化 JSON 协议进行报文编解码，直观展示了计算机网络应用层协议解耦不同软硬件平台的本质思想。")

heading("2 2 可靠性设计与安全机制原理", 2)
paragraph("为充分发挥 UDP 组播的高吞吐优势，同时保障在偶发网络抖动环境下的消息必达，本设计在应用层构建了轻量级的可靠传输保障机制。服务端向组播组发送群聊消息后，在内存中为每位在线成员记录一条待确认项，并设定 800 毫秒超时时间。客户端收到组播报文并验证无误后，立即通过可靠的 TCP 链路回传确认报文（ACK）。若 800 毫秒内服务端未收到某在线成员的 ACK，判定该成员需要可靠补偿，服务端立即通过该成员的 TCP 稳定连接将原消息单播补发一次。客户端维护最近接收的消息唯一标识（ID）缓存窗口，若同时收到组播与补发副本，自动过滤重复数据，实现“既享组播高效，又保消息必达”。")
paragraph("针对 TCP 字节流无消息边界的特性，本设计采用“4 字节大端整数长度头 + JSON 数据体”的定界机制。接收端循环读满 4 字节获得后续包体精确字节数 N，再精准读满 N 字节后交付反序列化，彻底解决粘包拆包问题。在数据安全与存储规范上，系统严格遵循现代网络安全准则，采用 16 字节高强度真随机盐值，并使用 PBKDF2-HMAC-SHA256 算法进行 200,000 次高强度迭代生成 32 字节派生散列存储于本地[2]。随机盐消除了彩虹表离线碰撞威胁，高迭代次数大幅拉高了暴力破解的时间成本。报文传输层引入 SHA-256 单向散列校验和，利用其显著的雪崩效应，单比特损坏或修改即导致散列值剧烈改变，接收端能准确识别并丢弃受损或篡改报文，保障数据完整性。")

heading("2 3 运行环境与网络配置规范", 2)
paragraph("系统实测环境为 Windows 操作系统、Python 3.10+ 标准环境（测试版本 3.14.7）、MinGW-w64 GCC 16.1.0。客户端仅依赖 Python 标准库，服务端提供预编译的静态可执行文件 bin/chat_server.exe，开箱即用。网络端口默认规划为 TCP 45860（认证与私聊）与 UDP 45861（群聊组播）。")
paragraph("组播数据报的 IP 首部 TTL（Time to Live，生存时间）严格设置为 1。这是计算机网络的核心控制机制：TTL=1 意味着组播数据包每经过一台路由器，TTL 就会减为 0 并被丢弃，从而保证组播通信严格限制在当前本地局域网（同一物理子网）内部，防止广播风暴外溢到广域网。在多电脑联机部署时，所有电脑连接同一 Wi-Fi 或交换机，客户端输入服务端局域网 IPv4 即可联机；若服务端具备多个网卡或虚拟网卡，可通过界面指定局域网网卡 IP，确保组播套接字绑定正确的出口网卡。")

heading("三 过程论述", page=True)
heading("3 1 模块结构与数据流", 2)
paragraph("为清晰说明账号控制通道、定向私聊单播通道与群聊组播通道的数据流向，图1给出了系统软件架构与数据流示意图。客户端采用多线程模型，主线程负责界面渲染与用户输入响应，网络后台线程负责套接字轮询接收，并通过线程安全队列将数据事件传递给主线程刷新控件[3]。")
figure(DOCS / "系统结构.png", "图1 聊天室模块结构与传输路径全景图")
paragraph("在数据流向中，客户端通过 TCP 链路向服务端发送注册、登录、拉取成员、发送聊天等请求。服务端验证身份后，将群聊数据向 UDP 组播地址广播，将定向私聊直接写入目标成员的 TCP 套接字；用户密码哈希持久化保存在服务端本地磁盘。客户端每 4 秒向服务端发送心跳报文，服务端维护读写超时检测，实现失联主动感知。表2汇总了工程核心模块的职责分工。")

table("表2 工程模块与职责分工", ["模块路径", "实现语言与职责说明"], [
    ("server_cpp/main.cpp", "C++17 服务端：底层 Winsock 并发调度、帧解析、会话状态、组播与重传队列"),
    ("lan_chat/protocol.py", "Python 协议层：应用层 LCP 1 编码、定界解码、标准化序列化与 SHA-256 校验"),
    ("lan_chat/client.py", "Python 网络层：TCP Socket 维护、UDP 组播组加入与收发、ACK 回传与消息去重"),
    ("lan_chat/gui.py", "Python 交互层：Tkinter 图形化界面、账号操作、群聊展示、好友多选定向私聊"),
    ("lan_chat/native_server.py", "Python 控制层：管理 C++ 服务端子进程的启动、日志捕获与优雅退出"),
    ("tests/test_chat.py", "自动化测试：12 项真实网络集成测试，检验粘包拆包、组播收发与异常容错")], [5.2, 10.5])

heading("3 2 账号与会话状态流转", 2)
paragraph("服务端采用面向连接的状态机管理客户端生命周期。连接建立后处于未认证状态，仅允许执行注册、登录与心跳请求；注册成功并不自动建立会话，需显式登录。登录成功后，连接与特定用户名绑定并加入全局在线列表，同时防止同一账号在多处重复登录。用户主动注销时，服务端清理会话并移除在线成员，但不删除磁盘账号文件。当网络异常中断或套接字读写超时到达时，服务端安全关闭连接，释放资源并向全网广播成员变动。")
paragraph("在并发控制方面，磁盘账号读写引入互斥锁，并在持久化时写入临时文件再执行原子文件替换，杜绝并发写入损坏文件；每个 TCP 连接的发送操作配置独立写锁，防止多线程同时写入导致数据帧交叉错乱；在线成员列表的推送采用串行化广播，确保新状态不会被过期的旧快照覆盖。")

heading("3 3 应用协议语法", 2)
paragraph("应用层协议命名为 LCP 1（LAN Chat Protocol v1）。TCP 帧采用“4 字节大端整数长度 N + N 字节 UTF-8 JSON 文本”的封装格式，N 的有效范围为 1 至 32768 字节。接收函数先循环读满 4 字节，再循环读满正文，彻底消除粘包拆包现象。UDP 组播数据报由于传输层本身保留了报文边界，直接封装 JSON 文本，不含 4 字节长度头。")

table("表3 报文顶层字段规范", ["字段", "数据类型与规格", "设计含义与作用"], [
    ("v", "整数，固定为 1", "协议版本号，便于未来平滑扩展"),
    ("id", "32 位小写十六进制字符串", "独立随机消息唯一标识符，用于去重与 ACK 确认"),
    ("type", "1 至 40 字符大写字符串", "业务任务类型码，区分具体操作"),
    ("ts", "0 至 2^53-1 范围的整数", "Unix 毫秒时间戳，供界面展示与调试使用"),
    ("body", "JSON 键值对对象", "具体业务参数载荷"),
    ("checksum", "64 位小写十六进制字符串", "除自身外其余 5 个字段的 SHA-256 完整性散列值")], [2.5, 6.1, 7.1])

paragraph("报文顶层规范化定义了表3所示的 6 个核心字段，具备严密的格式自洽性。对于格式缺失、字段冗余、非 UTF-8 编码或版本不符的数据，协议栈均予以规范化校验拦截。JSON 键名按字典序递归排序，采用紧凑分隔符，不转义中文。C++ 解析器设置了 JSON 嵌套深度阈值，防止恶意构造的超深对象消耗系统栈内存。")

heading("3 4 客户端任务语义", 2)
table("表4 客户端请求与状态设计", ["任务码", "body 主要参数", "语义说明与前置状态要求"], [
    ("REGISTER", "name, password", "未登录；用户名 1~20 字符，密码 6~128 字符；加盐哈希写入磁盘"),
    ("LOGIN", "name, password", "未登录；验证密码并排重在线；成功返回组播 IP 与端口"),
    ("LOGOUT", "空对象", "已登录；注销会话并清理重传项，保留磁盘账号数据"),
    ("MEMBERS", "空对象", "已登录；主动请求拉取当前最新在线成员完整列表"),
    ("CHAT", "text, mode=all, targets=[]", "已登录；群发消息，由服务端通过 UDP 组播分发给全员"),
    ("CHAT", "text, mode=selected, targets", "已登录；定向私聊，仅通过 TCP 单播发送给选中的 1~64 位在线好友"),
    ("ACK", "message_id", "已登录；确认收到特定群聊消息，供服务端清除超时重传项"),
    ("PING", "空对象", "任意连接状态；发送探活信令，服务端回复 PONG 维持连接")], [2.9, 5.3, 7.5])

paragraph("CHAT 消息正文规范为 1 至 2000 个字符且非全空白文本。定向私聊的目标列表会自动去重；若其中包含离线成员，系统实行事务性原子处理并及时提示发送方，保证收发双方认知的一致性。发送者身份由服务端会话上下文统一注入，从根源上保障了发送者身份的真实可信与不可篡改。连接内部维护最近请求 ID 记录，可有效拦截短时间内的重复操作。")

heading("3 5 服务端响应与错误处理", 2)
table("表5 服务端响应类型与字段含义", ["响应类型", "主要字段说明与业务含义"], [
    ("RESULT", "request 对应原请求 ID，action 标识操作类型，ok 表示成败，message 为提示文字"),
    ("登录 RESULT", "附加 name、group、udp_port、room_id，用于客户端自动配置并加入组播组"),
    ("聊天 RESULT", "附加 message_id，表示服务端已受理该请求，进入组播下发流程"),
    ("ROSTER", "members 为按字典序排列的完整在线成员名单，客户端收到后全局替换旧名单"),
    ("MESSAGE", "room_id、sender、text、mode、targets、recipients 等，实际接收的消息内容"),
    ("ERROR", "code 为机器识别错误码，message 为可读提示，request 为关联的原请求 ID"),
    ("PONG", "心跳响应，维持链路双向保活")], [3.3, 12.4])

table("表6 常见错误语义与系统容错策略", ["错误代码", "触发条件", "系统应对策略与连接状态"], [
    ("INVALID_TASK", "请求的 type 任务码未定义", "返回错误响应，保持连接正常，继续处理后续业务"),
    ("BAD_PACKET", "数据非合规 JSON 或 UTF-8 编码错误", "丢弃该帧数据，保持连接继续读取"),
    ("BAD_CHECKSUM", "SHA-256 散列值不匹配，数据遭篡改", "拒绝执行业务，返回错误，连接正常保留"),
    ("FRAME_TOO_LARGE", "数据帧长度小于等于 0 或大于 32KB", "判定为非法异常流量，主动断开异常连接"),
    ("BAD_BODY", "业务参数类型、字符长度不符合规范", "拒绝执行当前任务，连接保留"),
    ("AUTH_FAILED", "用户不存在或密码校验错误", "认证失败，当前连接保持未认证状态"),
    ("ALREADY_ONLINE", "该账号当前已在其他客户端登录中", "拒绝重复登录，避免多连接状态冲突"),
    ("NOT_LOGGED_IN", "未登录状态下尝试执行聊天业务", "拦截请求并提示需先完成登录认证"),
    ("STATE", "已登录状态下重复调用登录或注册", "提示当前状态冲突，要求先注销"),
    ("NO_RECIPIENT", "定向私聊目标列表为空或包含离线成员", "整条消息不予发送并提示检查好友状态"),
    ("REPLAY", "检测到重复提交的请求 ID", "拦截重复请求，不重复执行业务"),
    ("RATE_LIMIT", "单连接 1 秒内请求数超过 120 次", "触发限流保护，拒绝执行高频请求")], [4.2, 5.3, 6.2])

heading("3 6 完整性校验结构与算法", 2)
paragraph("发送方在构造报文时，提取 v、id、type、ts、body 五个字段，按键名递归进行字典序排列，以紧凑无多余空格的 UTF-8 编码格式序列化为字节串 M，计算其 SHA-256(M) 散列值，将得到的 32 字节哈希转换为 64 位小写十六进制字符串填入 checksum 字段。接收方在解析报文时，剥离 checksum 字段，执行完全相同的序列化并重新计算散列值进行比对。")
paragraph("报文处理遵循严格的流水线层次：先检查帧长度、再进行 UTF-8 解码与 JSON 解析、验证字段合法性、执行 SHA-256 散列完整性校验、检查任务码合法性、进行会话状态鉴权，最后执行业务逻辑。若单比特修改了 body.text 内容而保留原摘要，服务端能精准捕获 BAD_CHECKSUM；若构造了校验和正确但任务码未定义的报文，返回 INVALID_TASK。两类测试分别验证了语法完整性与语义容错性，服务端均能稳健运行而不退出。")

heading("3 7 组播确认与补发流程", 2)
paragraph("当服务端受理群聊请求时，获取当前在线成员快照，为每位在线成员创建以用户名与 MESSAGE.id 为键的待确认条目，截止时间设置为当前系统时间加上 800 毫秒，随后通过 UDP 套接字向组播组发送一次数据报。客户端收到合法消息后，先验证房间 ID 与接收名单，随后立即通过 TCP 连接回传 ACK 确认，并在本地利用滑动窗口去重后将消息渲染到界面。")
paragraph("服务端后台线程每隔 100 毫秒扫描一次待确认表。若超过 800 毫秒仍未收到某成员的 ACK 且该成员仍处于在线状态，服务端立即通过该成员的 TCP 连接将原消息作为单播补发一次，并移除待确认记录。客户端通过消息唯一 ID 进行全局去重，即使因网络抖动先后收到组播与 TCP 补发，也仅在界面渲染一次，在保障高可靠性的同时避免了刷屏干扰。")

heading("3 8 图形界面与实际运行", 2, page=True)
paragraph("系统图形界面采用清晰紧凑的单窗体布局，将账号认证、连接配置、聊天消息流、在线成员列表与输入发送区合理排布。图2展示了多用户登录后的中文群聊效果，图3通过多客户端收包记录直观证明了两人定向私聊对旁观者的物理级隔离。界面通过事件驱动模型将网络异步事件传递给主线程刷新控件，交互流畅无卡顿。")
figure(DOCS / "screenshots/群聊.png", "图2 中文群聊与在线成员界面效果")
figure(DOCS / "screenshots/定向隔离.png", "图3 两位目标与旁观者的实际接收记录对比")
paragraph("图2中的传输标记清晰区分了接收路径（UDP 组播或 TCP 补发），直观证明了局域网组播的实际生效。图3中“小周”与“小陈”作为定向私聊的目标成员，实时收到了私密消息；而作为第三方的“旁听同学”界面上仅保留正常的公共群聊，未收到任何私聊报文，验证了定向私聊的精准物理隔离。")

heading("四 结果分析", page=True)
heading("4 1 测试方法与实测结果", 2)
paragraph("系统构建了 12 项覆盖全面的自动化网络集成测试（tests/test_chat.py）。测试程序会真实启动编译好的 C++ 服务端可执行文件，并通过 Python 测试套件建立真实的 TCP 与 UDP 套接字连接进行通信校验。测试使用独立的临时磁盘数据库，执行完成后自动回收进程并清理环境。目前 12 项测试全部通过，测试覆盖了字符集编解码、篡改检测、格式容错、密码加盐、真实组播、私聊隔离、超时补发、粘包拆包定界以及服务端重启持久化等关键网络场景。")

table("表7 自动化测试覆盖与验证结果", ["编号", "测试检验场景", "网络原理与行为", "实测结果"], [
    ("01", "中英文与多行文本编解码", "UTF-8 原生编解码，校验跨语言报文一致性", "全部通过"),
    ("02", "报文篡改拦截测试", "单比特篡改正文，SHA-256 散列比对失败并安全丢弃", "全部通过"),
    ("03", "异常格式与超大报文拦截", "格式错误抛弃当前帧，超 32KB 帧断开异常连接", "全部通过"),
    ("04", "密码加盐与防重复登录", "PBKDF2 随机盐派生散列校验，拦截账号异地重登", "全部通过"),
    ("05", "真实 UDP 组播收发与去重", "向组播地址发送中文数据报，多客户端接收与窗口去重", "全部通过"),
    ("06", "定向多人私聊精准隔离", "向 2 位目标发送私聊，第 3 位旁观者无数据包流入", "全部通过"),
    ("07", "组播丢包应用层 TCP 补发", "客户端退出组播后，800ms 超时触发 TCP 单播补发", "全部通过"),
    ("08", "未知任务码与异常注入容错", "发送无效 type 后服务端返回错误，连接保持稳定", "全部通过"),
    ("09", "TCP 粘包与拆包定界恢复", "多帧粘连以及每 7 字节极限拆分，仍 100% 精准解帧", "全部通过"),
    ("10", "高危格式与匿名访问拦截", "未登录连接拦截聊天业务，连接池正常接纳新连接", "全部通过"),
    ("11", "业务边界与离线名单更新", "空白正文拦截，好友离线后实时触发名单全网同步", "全部通过"),
    ("12", "服务端重启数据持久化验证", "服务端进程重启后，读取 accounts.json 成功登录", "全部通过")], [1.2, 4.2, 9.2, 1.4])

heading("4 2 演示结果与工程解释", 2)
paragraph("在 3 分钟 720p 演示视频中，运行了一个 C++ 服务端与四个客户端实例。公共群聊由全部在线成员同步接收；定向私聊仅在被选中的“小周”与“小陈”的聊天区显示，其余旁观者完全被隔离。当手动退出某客户端的组播组以模拟网络抖动时，后续群聊消息在约 0.8 秒后通过该客户端的 TCP 单播稳定通道自动补发到达，聊天记录标记由 UDP 切换为 TCP，直观展现了应用层可靠性机制的有效性。")
figure(DOCS / "screenshots/异常拒绝.png", "图4 无效任务码与数据篡改被拒绝后系统继续稳定运行")
paragraph("图4展示了系统面对未知任务码与数据完整性校验失败时的容错表现。服务端在拦截非法请求并向客户端返回对应错误代码后，主服务进程与正常客户端连接完全不受影响，继续正常收发心跳与业务消息，具备高度的工程健壮性。")

heading("4 3 网络性能分析与部署建议", 2)
paragraph("在网络带宽占用方面，假定群聊在线人数为 N，单条群聊消息长度为 S。若采用传统的纯 TCP 单播群发，服务端需要发出的下行流量为 N * S；而采用 UDP 组播机制后，服务端发出的下行流量始终保持为固定的 1 * S，网络带宽利用率提升了约 N 倍，非常适合多人局域网通信。在实际多机部署时，需确保两台电脑处于同一局域网网段；若校园网 AP 开启了组播隔离，系统内置的 TCP 超时补发机制会自动作为保底手段生效，确保通信通畅。")

heading("五 课程设计总结")
paragraph("本课程设计通过结合面向连接的 TCP 控制通道与无连接的 UDP 组播通道，成功设计并实现了一套功能完备、原理清晰、运行健壮的局域网多人聊天室系统。设计贯穿了计算机网络各层核心机制：在传输层深入理解了 TCP 字节流与 UDP 数据报的本质区别，掌握了 IP 组播地址划分及 TTL 本地扩散控制原理；在应用层设计了严密的 4 字节定界机制解决粘包拆包问题，构建了基于 SHA-256 的报文完整性防篡改体系，并通过应用层 ACK 与超时重传机制，实现了弱网环境下的高可靠交付保证。")
paragraph("通过 Python 客户端与 C++ 服务端的跨语言协同开发，加深了对网络协议标准化重要性的认识——只要严格约定报文语法、序列化编码规则与状态机时序，不同语言与平台便能实现无缝互联互通。系统整体设计结构合理、代码规范，未来可在本系统基础上进一步引入 TLS 传输层安全通道、增加公私钥非对称端到端加密、支持断线自动重连与离线消息队列，使局域网通信系统迈向更高的安全性与工业级应用水平。")

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
