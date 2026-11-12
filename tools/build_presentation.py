"""Generate a professional course design presentation PPTX for the LAN Chat project."""
import os
from pathlib import Path
from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from pptx.enum.shapes import MSO_SHAPE

ROOT = Path(__file__).resolve().parent.parent
OUTPUT_PPTX = ROOT / "局域网聊天室课程设计答辩.pptx"

# Color Palette
NAVY = RGBColor(26, 54, 93)      # #1A365D - Primary headers & branding
TEAL = RGBColor(44, 122, 123)    # #2C7A7B - Secondary accent & badges
BLUE = RGBColor(49, 130, 206)    # #3182CE - Accent lines & icons
TEXT_DARK = RGBColor(45, 55, 72) # #2D3748 - Main body text
TEXT_MUTED = RGBColor(113, 128, 150) # #718096 - Subtitles & hints
CARD_BG = RGBColor(247, 250, 252) # #F7FAFC - Soft card fill
CARD_BORDER = RGBColor(226, 232, 240) # #E2E8F0 - Card borders
WHITE = RGBColor(255, 255, 255)
GREEN = RGBColor(56, 161, 105)
AMBER = RGBColor(221, 107, 32)

def set_slide_background(slide, color):
    background = slide.background
    fill = background.fill
    fill.solid()
    fill.fore_color.rgb = color

def add_header(slide, title_text, category_text="计算机网络课程设计 · 答辩汇报"):
    # Category tag
    cat_box = slide.shapes.add_textbox(Inches(0.8), Inches(0.4), Inches(8), Inches(0.35))
    tf_cat = cat_box.text_frame
    tf_cat.word_wrap = True
    tf_cat.margin_left = tf_cat.margin_right = tf_cat.margin_top = tf_cat.margin_bottom = 0
    p_cat = tf_cat.paragraphs[0]
    p_cat.text = category_text.upper()
    p_cat.font.name = "微软雅黑"
    p_cat.font.size = Pt(11)
    p_cat.font.bold = True
    p_cat.font.color.rgb = TEAL
    
    # Title
    title_box = slide.shapes.add_textbox(Inches(0.8), Inches(0.75), Inches(11.7), Inches(0.6))
    tf_title = title_box.text_frame
    tf_title.word_wrap = True
    tf_title.margin_left = tf_title.margin_right = tf_title.margin_top = tf_title.margin_bottom = 0
    p_title = tf_title.paragraphs[0]
    p_title.text = title_text
    p_title.font.name = "微软雅黑"
    p_title.font.size = Pt(22)
    p_title.font.bold = True
    p_title.font.color.rgb = NAVY
    
    # Accent underline
    line = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(0.8), Inches(1.42), Inches(1.5), Inches(0.04))
    line.fill.solid()
    line.fill.fore_color.rgb = BLUE
    line.line.color.rgb = BLUE

def add_card(slide, left, top, width, height, title="", title_color=NAVY, bg_color=CARD_BG, border_color=CARD_BORDER):
    card = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, left, top, width, height)
    card.fill.solid()
    card.fill.fore_color.rgb = bg_color
    card.line.color.rgb = border_color
    card.line.width = Pt(1.2)
    
    if title:
        tb = slide.shapes.add_textbox(left + Inches(0.25), top + Inches(0.2), width - Inches(0.5), Inches(0.4))
        tf = tb.text_frame
        tf.word_wrap = True
        tf.margin_left = tf.margin_right = tf.margin_top = tf.margin_bottom = 0
        p = tf.paragraphs[0]
        p.text = title
        p.font.name = "微软雅黑"
        p.font.size = Pt(14)
        p.font.bold = True
        p.font.color.rgb = title_color
    return card

def add_bullet_list(slide, left, top, width, height, items, font_size=12, text_color=TEXT_DARK, spacing=8):
    tb = slide.shapes.add_textbox(left, top, width, height)
    tf = tb.text_frame
    tf.word_wrap = True
    tf.margin_left = tf.margin_right = tf.margin_top = tf.margin_bottom = 0
    
    for i, item in enumerate(items):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.space_after = Pt(spacing)
        
        # Check if item has bold lead
        if "：" in item:
            lead, rest = item.split("：", 1)
            r_lead = p.add_run()
            r_lead.text = "• " + lead + "："
            r_lead.font.name = "微软雅黑"
            r_lead.font.size = Pt(font_size)
            r_lead.font.bold = True
            r_lead.font.color.rgb = NAVY
            
            r_rest = p.add_run()
            r_rest.text = rest
            r_rest.font.name = "微软雅黑"
            r_rest.font.size = Pt(font_size)
            r_rest.font.color.rgb = text_color
        else:
            r = p.add_run()
            r.text = "• " + item
            r.font.name = "微软雅黑"
            r.font.size = Pt(font_size)
            r.font.color.rgb = text_color
    return tb

def build_presentation():
    prs = Presentation()
    prs.slide_width = Inches(13.333)
    prs.slide_height = Inches(7.5)
    blank_layout = prs.slide_layouts[6] # Blank
    
    # ----------------------------------------------------
    # SLIDE 1: 封面
    # ----------------------------------------------------
    s1 = prs.slides.add_slide(blank_layout)
    set_slide_background(s1, WHITE)
    
    # Left decorative bar
    bar = s1.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(0), Inches(0), Inches(0.4), Inches(7.5))
    bar.fill.solid()
    bar.fill.fore_color.rgb = NAVY
    bar.line.fill.background()
    
    # Tag
    tb = s1.shapes.add_textbox(Inches(1.2), Inches(1.5), Inches(8), Inches(0.4))
    p = tb.text_frame.paragraphs[0]
    p.text = "计算机网络课程设计 · 课题答辩汇报"
    p.font.name = "微软雅黑"
    p.font.size = Pt(14)
    p.font.bold = True
    p.font.color.rgb = TEAL
    
    # Main Title
    tb = s1.shapes.add_textbox(Inches(1.2), Inches(2.0), Inches(11), Inches(1.4))
    tf = tb.text_frame
    tf.word_wrap = True
    p = tf.paragraphs[0]
    p.text = "局域网多人聊天室系统设计与实现"
    p.font.name = "微软雅黑"
    p.font.size = Pt(36)
    p.font.bold = True
    p.font.color.rgb = NAVY
    
    # Subtitle
    tb = s1.shapes.add_textbox(Inches(1.2), Inches(3.5), Inches(11), Inches(0.8))
    tf = tb.text_frame
    tf.word_wrap = True
    p = tf.paragraphs[0]
    p.text = "基于 TCP/UDP 双通道协同架构与应用层高可靠保障机制"
    p.font.name = "微软雅黑"
    p.font.size = Pt(18)
    p.font.color.rgb = TEXT_MUTED
    
    # Decorative line
    line = s1.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(1.2), Inches(4.3), Inches(3.0), Inches(0.05))
    line.fill.solid()
    line.fill.fore_color.rgb = BLUE
    line.line.fill.background()
    
    # Meta Info Cards
    card1 = add_card(s1, Inches(1.2), Inches(4.7), Inches(3.2), Inches(1.6), "技术架构", bg_color=CARD_BG)
    add_bullet_list(s1, Inches(1.45), Inches(5.3), Inches(2.8), Inches(0.9), [
        "C/S 客户机/服务器模式",
        "Python 客户端 + C++17 服务端"
    ], font_size=11, spacing=4)
    
    card2 = add_card(s1, Inches(4.7), Inches(4.7), Inches(3.2), Inches(1.6), "传输与控制", bg_color=CARD_BG)
    add_bullet_list(s1, Inches(4.95), Inches(5.3), Inches(2.8), Inches(0.9), [
        "UDP 局域网组播 (TTL=1)",
        "TCP 控制信令与定向私聊"
    ], font_size=11, spacing=4)
    
    card3 = add_card(s1, Inches(8.2), Inches(4.7), Inches(3.8), Inches(1.6), "自研应用层可靠性", bg_color=CARD_BG)
    add_bullet_list(s1, Inches(8.45), Inches(5.3), Inches(3.4), Inches(0.9), [
        "4 字节定界防粘包拆包",
        "ACK 超时补发 & SHA-256 防篡改"
    ], font_size=11, spacing=4)

    # ----------------------------------------------------
    # SLIDE 2: 目录
    # ----------------------------------------------------
    s2 = prs.slides.add_slide(blank_layout)
    set_slide_background(s2, WHITE)
    add_header(s2, "汇报目录 / Agenda")
    
    toc_items = [
        ("01", "选题背景与核心需求", "多人通信场景需求、系统功能矩阵与技术指标"),
        ("02", "总体架构与技术选型", "C/S 架构设计、跨语言协同开发与数据流向"),
        ("03", "核心网络原理：为什么选组播？", "TCP 单播 vs UDP 组播开销对比、TTL=1 局域网控制"),
        ("04", "核心网络原理：控制与定向私聊", "TCP 面向连接优势、选定多人定向发送与物理隔离"),
        ("05", "关键机制：定界、可靠性与防篡改", "4 字节防粘包拆包、ACK 超时补发、SHA-256 散列校验"),
        ("06", "自研应用层协议规范 (LCP 1)", "报文六元组结构、业务任务码与健全状态机容错"),
        ("07", "测试验证与验收演示", "12 项真实网络测试、粘包拆包/丢包补发实测演示"),
        ("08", "课程设计总结与技术心得", "计算机网络分层模型理解、跨语言编程经验与展望")
    ]
    
    for i, (num, title, desc) in enumerate(toc_items):
        col = i // 4
        row = i % 4
        left = Inches(1.0 + col * 5.8)
        top = Inches(1.8 + row * 1.3)
        
        # Num Badge
        badge = s2.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, left, top, Inches(0.65), Inches(0.55))
        badge.fill.solid()
        badge.fill.fore_color.rgb = NAVY
        badge.line.fill.background()
        tf = badge.text_frame
        p = tf.paragraphs[0]
        p.text = num
        p.alignment = PP_ALIGN.CENTER
        p.font.name = "微软雅黑"
        p.font.size = Pt(13)
        p.font.bold = True
        p.font.color.rgb = WHITE
        
        # Text block
        tb = s2.shapes.add_textbox(left + Inches(0.8), top - Inches(0.05), Inches(4.8), Inches(1.0))
        tf = tb.text_frame
        tf.word_wrap = True
        tf.margin_left = tf.margin_right = tf.margin_top = tf.margin_bottom = 0
        p1 = tf.paragraphs[0]
        p1.text = title
        p1.font.name = "微软雅黑"
        p1.font.size = Pt(13)
        p1.font.bold = True
        p1.font.color.rgb = NAVY
        
        p2 = tf.add_paragraph()
        p2.text = desc
        p2.font.name = "微软雅黑"
        p2.font.size = Pt(10)
        p2.font.color.rgb = TEXT_MUTED

    # ----------------------------------------------------
    # SLIDE 3: 01 选题背景与核心需求
    # ----------------------------------------------------
    s3 = prs.slides.add_slide(blank_layout)
    set_slide_background(s3, WHITE)
    add_header(s3, "01 选题背景与核心需求分析")
    
    add_card(s3, Inches(0.8), Inches(1.8), Inches(5.6), Inches(4.8), "局域网即时通信的设计需求", NAVY)
    add_bullet_list(s3, Inches(1.1), Inches(2.5), Inches(5.0), Inches(3.8), [
        "群聊下行带宽开销优化：若使用纯 TCP 单播，群内有 N 人时，服务端每发一条消息需复制 N 次，出口带宽与 CPU 随人数呈 O(N) 线性增长。",
        "网络边界控制要求：局域网聊天必须防止数据外溢扩散，避免对外部广域网引发广播风暴。",
        "私密交流的定向隔离：用户常常需要与选定的多位好友私聊，未被选中的第三方用户在物理链路上绝不能收到该报文。",
        "传输自愈与数据完整性：充分结合底层传输层特性，在应用层构建自适应定界、超时补偿与防篡改验证体系。"
    ], font_size=12, spacing=10)
    
    add_card(s3, Inches(6.8), Inches(1.8), Inches(5.7), Inches(4.8), "系统设计目标与功能矩阵", TEAL)
    add_bullet_list(s3, Inches(7.1), Inches(2.5), Inches(5.1), Inches(3.8), [
        "用户体系与安全存储：支持图形化注册、密码校验、在线状态绑定与注销；密码采用 PBKDF2 加盐安全存储，符合信息安全规范。",
        "在线成员动态感知：服务端维护全局在线会话，成员上线/下线自动向全网实时推送最新名单。",
        "双模通信能力：支持基于 UDP 组播的高带宽公共群聊，以及基于 TCP 单播的选定多人定向私聊。",
        "应用层可靠性闭环：实现定长头部定界（解粘包拆包）、ACK 确认应答、800ms 超时 TCP 补发以及 SHA-256 完整性防篡改。"
    ], font_size=12, spacing=10)

    # ----------------------------------------------------
    # SLIDE 4: 02 总体架构与技术选型
    # ----------------------------------------------------
    s4 = prs.slides.add_slide(blank_layout)
    set_slide_background(s4, WHITE)
    add_header(s4, "02 总体系统架构与技术选型")
    
    add_card(s4, Inches(0.8), Inches(1.8), Inches(3.7), Inches(4.8), "Python 图形客户端", BLUE)
    add_bullet_list(s4, Inches(1.05), Inches(2.5), Inches(3.2), Inches(3.8), [
        "轻量交互：采用内置 Tkinter 快速构建直观图形界面，单机运行无需额外安装第三方依赖包。",
        "双线程架构：主线程专注 UI 渲染与用户交互；后台子线程负责网络套接字监听，通过线程安全队列解耦交互。",
        "智能去重：维护滑动窗口缓存已接收消息 ID，自动消除组播与重传的重复消息。"
    ], font_size=11, spacing=8)
    
    add_card(s4, Inches(4.8), Inches(1.8), Inches(3.7), Inches(4.8), "C++17 高性能服务端", NAVY)
    add_bullet_list(s4, Inches(5.05), Inches(2.5), Inches(3.2), Inches(3.8), [
        "原生网络 I/O：基于 Windows 原生 Winsock2 API，支持多连接高并发套接字调度与超时监测。",
        "会话与状态机：管理用户登录状态、在线成员快照、每连接独立写锁（防止帧交叉）。",
        "组播与补发调度：负责群聊组播发送，并在独立定时线程中执行 800ms ACK 超时检测与单播补发。"
    ], font_size=11, spacing=8)
    
    add_card(s4, Inches(8.8), Inches(1.8), Inches(3.7), Inches(4.8), "规范化应用层协议 LCP 1", TEAL)
    add_bullet_list(s4, Inches(9.05), Inches(2.5), Inches(3.2), Inches(3.8), [
        "跨语言解耦：统一采用 UTF-8 编码的标准 JSON 报文格式，彻底打破 C++ 与 Python 语言屏障。",
        "帧定界机制：TCP 采用 4 字节大端整数指明报文长度，循环阻塞读满，彻底消除粘包拆包。",
        "完整性防篡改：字段字典序排列并计算 SHA-256 散列，单比特修改即拒绝执行业务。"
    ], font_size=11, spacing=8)

    # ----------------------------------------------------
    # SLIDE 5: 03 核心网络原理：为什么选组播？
    # ----------------------------------------------------
    s5 = prs.slides.add_slide(blank_layout)
    set_slide_background(s5, WHITE)
    add_header(s5, "03 核心原理 ①：为什么群发采用 UDP 组播？")
    
    # Comparison Cards
    c1 = add_card(s5, Inches(0.8), Inches(1.8), Inches(5.6), Inches(3.0), "纯 TCP 单播群发开销分析", AMBER)
    add_bullet_list(s5, Inches(1.1), Inches(2.4), Inches(5.0), Inches(2.2), [
        "线性开销：当群内有 N 个在线用户时，服务端转发单条消息需在 N 条连接上重复发送 N 次（O(N) 带宽与 CPU 占用）。",
        "传输瓶颈：在并发规模扩大时，网络出口带宽与服务器 I/O 压力成倍上升。"
    ], font_size=12, spacing=8)
    
    c2 = add_card(s5, Inches(6.8), Inches(1.8), Inches(5.7), Inches(3.0), "UDP 局域网硬件级组播方案", GREEN)
    add_bullet_list(s5, Inches(7.1), Inches(2.4), Inches(5.1), Inches(2.2), [
        "硬件分发：服务端仅向组播地址（239.255.42.99:45861）发送 1 次数据报（O(1) 恒定开销）。",
        "底层复制：局域网交换机/网卡硬件根据 IGMP 自动向所有加入组的成员复制分发，成倍节省网络带宽！"
    ], font_size=12, spacing=8)
    
    # Bottom Card on TTL
    c_ttl = add_card(s5, Inches(0.8), Inches(5.1), Inches(11.7), Inches(1.6), "TTL=1 局域网范围控制网络原理", NAVY)
    add_bullet_list(s5, Inches(1.1), Inches(5.7), Inches(11.1), Inches(0.9), [
        "生存时间原理：IP 报文首部的 TTL（Time to Live）严格设为 1。数据包经过首台路由器时，TTL 减为 0 被直接丢弃。",
        "网络安全效果：严格限制群聊流量仅在本地物理子网内传播，绝不外溢到广域网，彻底避免对外部网络造成广播风暴。"
    ], font_size=11, spacing=4)

    # ----------------------------------------------------
    # SLIDE 6: 04 核心网络原理：控制与定向私聊
    # ----------------------------------------------------
    s6 = prs.slides.add_slide(blank_layout)
    set_slide_background(s6, WHITE)
    add_header(s6, "04 核心原理 ②：控制信令与定向私聊采用 TCP")
    
    add_card(s6, Inches(0.8), Inches(1.8), Inches(5.6), Inches(4.8), "控制信令为什么必须用 TCP？", NAVY)
    add_bullet_list(s6, Inches(1.1), Inches(2.5), Inches(5.0), Inches(3.8), [
        "面向连接的可靠交付：TCP 经过三次握手建立端到端虚电路，具备滑动窗口确认、超时重传与顺序控制机制。",
        "状态绝对一致性：用户注册鉴权、密码核验、在线成员列表同步关系到全局系统状态，决不能容忍丢失或乱序。",
        "连接保活与探活：客户端每 4 秒发送 PING 心跳，服务端维护读写超时检测，客户端断电或拔线可主动感知并剔除。"
    ], font_size=12, spacing=10)
    
    add_card(s6, Inches(6.8), Inches(1.8), Inches(5.7), Inches(4.8), "定向私聊的物理级精准隔离原理", TEAL)
    add_bullet_list(s6, Inches(7.1), Inches(2.5), Inches(5.1), Inches(3.8), [
        "单播精准定向：在客户端列表多选好友后，报文通过 TCP 发送给服务端，服务端仅向被选中的好友 TCP 套接字逐个推送单播。",
        "链路级数据隔离：未被选中的第三方客户端在物理网络链路上根本不会收到该数据包，从底层网络层面保障了通信隐私。",
        "清晰回显支持：私聊消息同步回显给发送者本人，并明确标注接收人列表，提升用户沟通体验。"
    ], font_size=12, spacing=10)

    # ----------------------------------------------------
    # SLIDE 7: 05 关键机制 ①：解决 TCP 粘包与拆包
    # ----------------------------------------------------
    s7 = prs.slides.add_slide(blank_layout)
    set_slide_background(s7, WHITE)
    add_header(s7, "05 关键机制 ①：解决 TCP 粘包与拆包定界原理")
    
    add_card(s7, Inches(0.8), Inches(1.8), Inches(5.6), Inches(4.8), "TCP 字节流传输特性与定界设计", AMBER)
    add_bullet_list(s7, Inches(1.1), Inches(2.5), Inches(5.0), Inches(3.8), [
        "字节流本质：TCP 是面向字节流（Byte Stream）的传输层协议，传输层并不维护应用层消息的结构边界。",
        "粘包现象（Coalescing）：发送方连续发送多个小数据包时，Nagle 算法或内核发送缓冲可能将其合并为一个 TCP 报文发出。",
        "拆包现象（Fragmentation）：当单个大数据包超过链路 MTU 或内核缓冲区满时，数据包会被强行拆分成多个网络分段传输。",
        "边界识别需求：应用层协议必须具备自包含的定界规则，确保接收端能够无歧义地还原出原始的每个业务报文。"
    ], font_size=12, spacing=8)
    
    add_card(s7, Inches(6.8), Inches(1.8), Inches(5.7), Inches(4.8), "4 字节长度前缀定界法（彻底解决）", GREEN)
    add_bullet_list(s7, Inches(7.1), Inches(2.5), Inches(5.1), Inches(3.8), [
        "帧结构设计：[ 4 字节包体长度 N (uint32_be) ] + [ N 字节 JSON 数据体 ]。",
        "网络大端字节序：统一采用大端序（Big-Endian），保证不同架构主机对高低位字节的解析完全一致。",
        "两阶段循环读取：\n  1. 循环阻塞读取，精准读满 4 字节，计算出包体长度 N；\n  2. 循环阻塞读取，精准收集满 N 字节后交付反序列化。",
        "极限测试验证：自动化测试用例 test_09 模拟了多帧粘连以及每次仅发送 7 字节的极端拆包，系统仍 100% 精准解帧！"
    ], font_size=11, spacing=8)

    # ----------------------------------------------------
    # SLIDE 8: 06 关键机制 ②：UDP 组播可靠性保障
    # ----------------------------------------------------
    s8 = prs.slides.add_slide(blank_layout)
    set_slide_background(s8, WHITE)
    add_header(s8, "06 关键机制 ②：UDP 组播可靠性保障 (ACK + 补发)")
    
    # 3 step flow cards
    w_card = Inches(3.7)
    add_card(s8, Inches(0.8), Inches(1.8), w_card, Inches(4.8), "步骤 1：组播发送与超时登记", NAVY)
    add_bullet_list(s8, Inches(1.05), Inches(2.5), Inches(3.2), Inches(3.8), [
        "组播下发：服务端受理群聊请求后，向组播地址发送一次 UDP 数据报。",
        "记录待确认项：获取当前在线成员快照，为每位在线成员记录待确认条目：(用户名, 消息ID)。",
        "启动定时器：设定超时截止时间为：当前时间 + 800 毫秒。"
    ], font_size=11, spacing=8)
    
    add_card(s8, Inches(4.8), Inches(1.8), w_card, Inches(4.8), "步骤 2：客户端校验与 ACK 应答", BLUE)
    add_bullet_list(s8, Inches(5.05), Inches(2.5), Inches(3.2), Inches(3.8), [
        "正常收包：客户端在组播套接字接收到消息，验证房间 ID 与接收名单合法。",
        "回传 ACK：客户端立即通过稳定的 TCP 通道向服务端回传 ACK 确认报文。",
        "清除记录：服务端收到 ACK 后，从待确认表中即时清除该用户的超时条目。"
    ], font_size=11, spacing=8)
    
    add_card(s8, Inches(8.8), Inches(1.8), w_card, Inches(4.8), "步骤 3：超时自适应单播补发", TEAL)
    add_bullet_list(s8, Inches(9.05), Inches(2.5), Inches(3.2), Inches(3.8), [
        "超时感知：服务端后台线程每 100ms 巡检，若 800ms 内未收到某成员的 ACK，触发可靠性补偿流程。",
        "单播重传：通过该成员的 TCP 稳定连接将原消息补发一次，确保消息必达！",
        "窗口去重：客户端维护已接收消息 ID 缓存，自动过滤重复数据，杜绝重复渲染。"
    ], font_size=11, spacing=8)

    # ----------------------------------------------------
    # SLIDE 9: 07 关键机制 ③：SHA-256 完整性防篡改与加盐存储
    # ----------------------------------------------------
    s9 = prs.slides.add_slide(blank_layout)
    set_slide_background(s9, WHITE)
    add_header(s9, "07 关键机制 ③：数据完整性校验与安全加盐存储")
    
    add_card(s9, Inches(0.8), Inches(1.8), Inches(5.6), Inches(4.8), "SHA-256 报文完整性校验机制", NAVY)
    add_bullet_list(s9, Inches(1.1), Inches(2.5), Inches(5.0), Inches(3.8), [
        "报文完整性保障：局域网传输可能因信号干扰发生比特翻转，需在应用层建立自验证机制。",
        "标准化序列化：提取 v, id, type, ts, body 五字段，键名严格按字典序排序，生成规范化紧凑 UTF-8 字节流。",
        "单向散列与雪崩效应：计算 SHA-256 摘要存入 checksum。任何单比特改动都会导致散列值突变。",
        "安全拦截：接收端以相同规则重算比对，若不吻合立即返回 BAD_CHECKSUM 并丢弃，保护系统安全。"
    ], font_size=11, spacing=8)
    
    add_card(s9, Inches(6.8), Inches(1.8), Inches(5.7), Inches(4.8), "PBKDF2 加盐安全密码存储体系", TEAL)
    add_bullet_list(s9, Inches(7.1), Inches(2.5), Inches(5.1), Inches(3.8), [
        "规范化高强度密码防护：遵循信息安全标准，坚决杜绝明文存储与弱哈希算法。",
        "16 字节随机盐值 (Salt)：注册时为每个账号生成高强度真随机盐，彻底消除了相同密码生成相同散列的缺陷，彩虹表彻底失效！",
        "200,000 次高强度迭代：基于 HMAC-SHA256 循环迭代 20 万次，大幅增加哈希运算耗时，极大抬高了暴力字典破解的攻击成本。"
    ], font_size=11, spacing=8)

    # ----------------------------------------------------
    # SLIDE 10: 08 自研应用层协议 LCP 1 规范
    # ----------------------------------------------------
    s10 = prs.slides.add_slide(blank_layout)
    set_slide_background(s10, WHITE)
    add_header(s10, "08 自研应用层协议 LCP 1 (LAN Chat Protocol)")
    
    # Left: Field table card
    add_card(s10, Inches(0.8), Inches(1.8), Inches(6.0), Inches(4.8), "统一六元组报文封装结构", NAVY)
    
    table_shape = s10.shapes.add_table(7, 3, Inches(1.0), Inches(2.5), Inches(5.6), Inches(3.8))
    t = table_shape.table
    t.columns[0].width = Inches(1.2)
    t.columns[1].width = Inches(1.4)
    t.columns[2].width = Inches(3.0)
    
    headers = [("字段", "类型", "设计含义与约束")]
    rows = [
        ("v", "int", "协议版本号，固定为 1"),
        ("id", "string", "32 位随机 UUID，消息去重与 ACK 标识"),
        ("type", "string", "大写任务码，如 LOGIN, CHAT, ACK"),
        ("ts", "int64", "Unix 毫秒时间戳，展示与记录"),
        ("body", "object", "具体业务参数载荷 (Payload)"),
        ("checksum", "string", "其余五字段的 SHA-256 散列摘要")
    ]
    for r_idx, row in enumerate(headers + rows):
        for c_idx, val in enumerate(row):
            cell = t.cell(r_idx, c_idx)
            cell.text = val
            cell.vertical_anchor = MSO_ANCHOR.MIDDLE
            p = cell.text_frame.paragraphs[0]
            p.font.name = "微软雅黑"
            p.font.size = Pt(10)
            if r_idx == 0:
                p.font.bold = True
                p.font.color.rgb = WHITE
                cell.fill.solid()
                cell.fill.fore_color.rgb = NAVY
            else:
                p.font.color.rgb = TEXT_DARK
                cell.fill.solid()
                cell.fill.fore_color.rgb = WHITE if r_idx % 2 == 1 else CARD_BG
    
    # Right: Error handling card
    add_card(s10, Inches(7.1), Inches(1.8), Inches(5.4), Inches(4.8), "完备状态机与优雅容错设计", TEAL)
    add_bullet_list(s10, Inches(7.35), Inches(2.5), Inches(4.9), Inches(3.8), [
        "连接状态清晰：未登录 -> 登录在线 -> 注销会话，状态机严格约束不同阶段允许调用的操作。",
        "细分错误码体系：\n  • BAD_PACKET: 格式错误，丢弃坏帧保留连接\n  • BAD_CHECKSUM: 散列不符，拦截篡改报文\n  • INVALID_TASK: 未知任务码，安全返回错误\n  • FRAME_TOO_LARGE: 超 32KB 帧，主动切断连接",
        "优雅容错：遇到恶意或损坏报文时，系统绝不抛出未捕获异常，主服务与正常客户端连接持续稳定运行！"
    ], font_size=11, spacing=8)

    # ----------------------------------------------------
    # SLIDE 11: 09 自动化集成测试与实测验证
    # ----------------------------------------------------
    s11 = prs.slides.add_slide(blank_layout)
    set_slide_background(s11, WHITE)
    add_header(s11, "09 自动化网络集成测试验证 (12 项用例全部通过)")
    
    # Table of 12 tests
    table_shape = s11.shapes.add_table(7, 4, Inches(0.8), Inches(1.8), Inches(11.7), Inches(4.8))
    t = table_shape.table
    t.columns[0].width = Inches(1.0)
    t.columns[1].width = Inches(3.2)
    t.columns[2].width = Inches(6.0)
    t.columns[3].width = Inches(1.5)
    
    headers = [("编号", "测试场景", "检验原理与网络行为", "实测结果")]
    rows = [
        ("01-02", "中英文编解码 & 报文篡改拦截", "UTF-8 原生编解码；修改正文单比特触发 BAD_CHECKSUM 拦截", "全部通过"),
        ("03-04", "格式容错 & 密码加盐校验", "超大报文主动切断连接；PBKDF2 随机盐验证，拦截异地重复登录", "全部通过"),
        ("05-06", "真实 UDP 组播 & 定向私聊隔离", "组播收发与窗口去重；定向私聊仅目标收到，旁观者物理级隔离", "全部通过"),
        ("07-08", "组播丢包补发 & 异常任务码容错", "退出组播后 800ms 触发 TCP 补发；未知 type 正常响应不崩溃", "全部通过"),
        ("09-10", "TCP 粘包拆包定界 & 匿名访问拦截", "极限 7 字节拆包与多帧粘包 100% 精准还原；未登录请求拦截", "全部通过"),
        ("11-12", "成员离线同步 & 进程重启持久化", "好友断开实时全网推名单；C++ 进程重启后成功读盘认证登录", "全部通过")
    ]
    for r_idx, row in enumerate(headers + rows):
        for c_idx, val in enumerate(row):
            cell = t.cell(r_idx, c_idx)
            cell.text = val
            cell.vertical_anchor = MSO_ANCHOR.MIDDLE
            p = cell.text_frame.paragraphs[0]
            p.font.name = "微软雅黑"
            p.font.size = Pt(11)
            if r_idx == 0:
                p.font.bold = True
                p.font.color.rgb = WHITE
                cell.fill.solid()
                cell.fill.fore_color.rgb = NAVY
            else:
                if c_idx == 3:
                    p.font.bold = True
                    p.font.color.rgb = GREEN
                else:
                    p.font.color.rgb = TEXT_DARK
                cell.fill.solid()
                cell.fill.fore_color.rgb = WHITE if r_idx % 2 == 1 else CARD_BG

    # ----------------------------------------------------
    # SLIDE 12: 10 实际运行效果与验收演示
    # ----------------------------------------------------
    s12 = prs.slides.add_slide(blank_layout)
    set_slide_background(s12, WHITE)
    add_header(s12, "10 实际运行效果与验收演示")
    
    add_card(s12, Inches(0.8), Inches(1.8), Inches(3.7), Inches(4.8), "功能 ①：中文群聊与组播直达", BLUE)
    add_bullet_list(s12, Inches(1.05), Inches(2.5), Inches(3.2), Inches(3.8), [
        "公共交流：所有客户端点击“群发”后，在线成员几乎零延迟同步接收。",
        "网络层标识：聊天消息流中明确显示 [UDP 组播] 标记，证实数据真正走组播硬件分发。",
        "换行与表情：完美支持中英文字符、多行换行与符号正常渲染。"
    ], font_size=11, spacing=10)
    
    add_card(s12, Inches(4.8), Inches(1.8), Inches(3.7), Inches(4.8), "功能 ②：选定多人定向私聊", NAVY)
    add_bullet_list(s12, Inches(5.05), Inches(2.5), Inches(3.2), Inches(3.8), [
        "灵活多选：在成员列表中按住 Ctrl 或单击，勾选 1 位或多位目标好友。",
        "精准推达：仅有被勾选的好友及发送者本人收到该私聊消息。",
        "旁观者隔离：第三方旁观者界面毫无波动，底层网络完全无数据包流入！"
    ], font_size=11, spacing=10)
    
    add_card(s12, Inches(8.8), Inches(1.8), Inches(3.7), Inches(4.8), "功能 ③：网络自愈与可靠回退", TEAL)
    add_bullet_list(s12, Inches(9.05), Inches(2.5), Inches(3.2), Inches(3.8), [
        "故障模拟：测试中主动让客户端退出组播组，模拟局域网丢包或网卡故障。",
        "超时重传：约 0.8 秒后，服务端通过该客户端的 TCP 单播通道自动完成补发。",
        "状态标记：该条补发消息明确展示为 [TCP]，证明保底机制无缝生效！"
    ], font_size=11, spacing=10)

    # ----------------------------------------------------
    # SLIDE 13: 11 课程设计总结与技术体会
    # ----------------------------------------------------
    s13 = prs.slides.add_slide(blank_layout)
    set_slide_background(s13, WHITE)
    add_header(s13, "11 课程设计总结与技术体会")
    
    add_card(s13, Inches(0.8), Inches(1.8), Inches(5.6), Inches(4.8), "理论结合实践的核心收获", NAVY)
    add_bullet_list(s13, Inches(1.1), Inches(2.5), Inches(5.0), Inches(3.8), [
        "深化分层模型认知：深刻理解了传输层 TCP（面向连接/流式）与 UDP（无连接/数据报）的本质区别，体会到在不同业务场景下的权衡与互补。",
        "掌握局域网多播原理：亲手配置了 Class D 类组播地址、网卡成员加入（IGMP）与 TTL=1 本地广播域控制。",
        "攻克流式传输核心难题：自研 4 字节大端长度前缀定界，彻底解决了网络编程中最容易遇到的粘包拆包问题。",
        "跨语言协议标准化：深刻体会到“协议是网络通信的灵魂”——只要严格规范报文语法与时序，不同编程语言能够完美协同。"
    ], font_size=12, spacing=10)
    
    add_card(s13, Inches(6.8), Inches(1.8), Inches(5.7), Inches(4.8), "未来系统演进与拓展方向", TEAL)
    add_bullet_list(s13, Inches(7.1), Inches(2.5), Inches(5.1), Inches(3.8), [
        "TLS 传输层加密：在 TCP 连接上建立 TLS 握手，实现全链路防窃听与防中间人攻击。",
        "非对称端到端加密：引入 RSA/ECC 公私钥体系，私聊消息实现端到端加密，即便服务器也无法窥视正文。",
        "离线消息队列：为离线用户建立基于 SQLite/Redis 的持久化消息存储，实现上线自动拉取历史。",
        "断线重连与网络自愈：在客户端加入指数退避重连机制，网络波动恢复后自动重新入会。"
    ], font_size=12, spacing=10)

    # ----------------------------------------------------
    # SLIDE 14: 12 答辩致谢
    # ----------------------------------------------------
    s14 = prs.slides.add_slide(blank_layout)
    set_slide_background(s14, WHITE)
    
    # Left decorative bar
    bar = s14.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(0), Inches(0), Inches(0.4), Inches(7.5))
    bar.fill.solid()
    bar.fill.fore_color.rgb = NAVY
    bar.line.fill.background()
    
    tb = s14.shapes.add_textbox(Inches(1.5), Inches(2.2), Inches(10), Inches(1.5))
    tf = tb.text_frame
    p = tf.paragraphs[0]
    p.text = "汇报完毕 · 谢谢各位老师评审！"
    p.font.name = "微软雅黑"
    p.font.size = Pt(36)
    p.font.bold = True
    p.font.color.rgb = NAVY
    
    tb2 = s14.shapes.add_textbox(Inches(1.5), Inches(3.8), Inches(10), Inches(1.0))
    tf2 = tb2.text_frame
    p2 = tf2.paragraphs[0]
    p2.text = "诚恳接受各位老师的批评、指导与提问 (Q & A)"
    p2.font.name = "微软雅黑"
    p2.font.size = Pt(18)
    p2.font.color.rgb = TEXT_MUTED
    
    line = s14.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(1.5), Inches(4.7), Inches(2.5), Inches(0.04))
    line.fill.solid()
    line.fill.fore_color.rgb = BLUE
    line.line.fill.background()
    
    prs.save(OUTPUT_PPTX)
    print(f"Presentation saved to {OUTPUT_PPTX}")

if __name__ == "__main__":
    build_presentation()
