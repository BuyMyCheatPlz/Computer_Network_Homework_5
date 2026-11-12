// LCP/1 native Windows server. Build with MinGW-w64 or MSVC, C++17.
#define WIN32_LEAN_AND_MEAN
#define NOMINMAX
#include <winsock2.h>
#include <ws2tcpip.h>
#include <windows.h>
#include <bcrypt.h>
#include "vendor/json.hpp"
#include <algorithm>
#include <atomic>
#include <chrono>
#include <deque>
#include <filesystem>
#include <fstream>
#include <iostream>
#include <map>
#include <memory>
#include <mutex>
#include <set>
#include <string>
#include <thread>
#include <vector>

using json = nlohmann::json;
using Clock = std::chrono::steady_clock;
constexpr size_t MAX_FRAME = 32768;
struct Error : std::runtime_error {
    std::string code;
    Error(std::string c, std::string m) : runtime_error(m), code(std::move(c)) {}
};
std::mutex log_mutex;
void log(const std::string& text) {
    std::lock_guard<std::mutex> guard(log_mutex);
    std::cout << text << std::endl;
}
std::string hex(const std::vector<unsigned char>& bytes) {
    const char* digits = "0123456789abcdef";
    std::string result;
    for (auto b : bytes) { result += digits[b >> 4]; result += digits[b & 15]; }
    return result;
}
std::vector<unsigned char> random_bytes(size_t size) {
    std::vector<unsigned char> result(size);
    if (BCryptGenRandom(nullptr, result.data(), ULONG(size), BCRYPT_USE_SYSTEM_PREFERRED_RNG) < 0)
        throw std::runtime_error("BCryptGenRandom failed");
    return result;
}
std::string sha256(const std::string& input) {
    BCRYPT_ALG_HANDLE alg = nullptr;
    BCRYPT_HASH_HANDLE hash = nullptr;
    if (BCryptOpenAlgorithmProvider(&alg, BCRYPT_SHA256_ALGORITHM, nullptr, 0) < 0)
        throw std::runtime_error("SHA256 provider failed");
    std::vector<unsigned char> output(32);
    NTSTATUS status = BCryptCreateHash(alg, &hash, nullptr, 0, nullptr, 0, 0);
    if (status >= 0) status = BCryptHashData(hash, (PUCHAR)input.data(), ULONG(input.size()), 0);
    if (status >= 0) status = BCryptFinishHash(hash, output.data(), ULONG(output.size()), 0);
    if (hash) BCryptDestroyHash(hash);
    BCryptCloseAlgorithmProvider(alg, 0);
    if (status < 0) throw std::runtime_error("SHA256 failed");
    return hex(output);
}
bool equal_digest(const std::string& a, const std::string& b) {
    if (a.size() != b.size()) return false;
    unsigned char diff = 0;
    for (size_t i = 0; i < a.size(); ++i) diff |= a[i] ^ b[i];
    return diff == 0;
}
std::string derive(const std::string& password, const std::string& salt_hex) {
    if (salt_hex.size() != 32) throw std::runtime_error("invalid account salt");
    std::vector<unsigned char> salt(16), digest(32);
    for (size_t i = 0; i < 16; ++i) salt[i] = (unsigned char)std::stoul(salt_hex.substr(i * 2, 2), nullptr, 16);
    BCRYPT_ALG_HANDLE alg = nullptr;
    if (BCryptOpenAlgorithmProvider(&alg, BCRYPT_SHA256_ALGORITHM, nullptr, BCRYPT_ALG_HANDLE_HMAC_FLAG) < 0)
        throw std::runtime_error("PBKDF2 provider failed");
    NTSTATUS result = BCryptDeriveKeyPBKDF2(alg, (PUCHAR)password.data(), ULONG(password.size()),
                           salt.data(), ULONG(salt.size()), 200000, digest.data(), ULONG(digest.size()), 0);
    BCryptCloseAlgorithmProvider(alg, 0);
    if (result < 0) throw std::runtime_error("PBKDF2 failed");
    return hex(digest);
}
// Valid JSON UTF-8 is checked by nlohmann; count Unicode code points.
std::vector<unsigned> codepoints(const std::string& s) {
    std::vector<unsigned> result;
    for (size_t i = 0; i < s.size();) {
        unsigned char c = s[i++]; unsigned cp = c; int count = 0;
        if (c >= 0xf0) { cp = c & 7; count = 3; }
        else if (c >= 0xe0) { cp = c & 15; count = 2; }
        else if (c >= 0xc0) { cp = c & 31; count = 1; }
        while (count-- && i < s.size()) cp = (cp << 6) | (s[i++] & 63);
        result.push_back(cp);
    }
    return result;
}
bool valid_name(const std::string& name) {
    auto chars = codepoints(name);
    if (chars.empty() || chars.size() > 20) return false;
    for (auto c : chars)
        if (!((c >= 'a' && c <= 'z') || (c >= 'A' && c <= 'Z') || (c >= '0' && c <= '9') ||
              c == '_' || c == '-' || (c >= 0x4e00 && c <= 0x9fff))) return false;
    return true;
}
bool hexadecimal(const std::string& s, size_t size) {
    return s.size() == size && s.find_first_not_of("0123456789abcdef") == std::string::npos;
}
json packet(const std::string& type, json body = json::object()) {
    auto ms = std::chrono::duration_cast<std::chrono::milliseconds>(std::chrono::system_clock::now().time_since_epoch()).count();
    json p = {{"v", 1}, {"id", hex(random_bytes(16))}, {"type", type}, {"ts", ms}, {"body", body}};
    p["checksum"] = sha256(p.dump());
    return p;
}
json parse(const std::string& raw) {
    try {
        std::map<int, std::set<std::string>> keys;
        auto callback = [&keys](int depth, json::parse_event_t event, json& parsed) {
            if (depth > 32) throw Error("BAD_PACKET", "JSON nesting exceeds 32");
            if (event == json::parse_event_t::object_start) keys[depth + 1].clear();
            if (event == json::parse_event_t::key && !keys[depth].insert(parsed.get<std::string>()).second)
                throw Error("BAD_PACKET", "Duplicate JSON key");
            return true;
        };
        json p = json::parse(raw, callback);
        if (!p.is_object() || p.size() != 6 || !p.contains("v") || !p.contains("id") ||
                !p.contains("type") || !p.contains("ts") || !p.contains("body") || !p.contains("checksum"))
            throw Error("BAD_PACKET", "Invalid envelope fields");
        if (!p["v"].is_number_integer() || p["v"] != 1 || !p["body"].is_object() ||
                !p["id"].is_string() || !hexadecimal(p["id"], 32) || !p["type"].is_string() ||
                p["type"].get<std::string>().empty() || p["type"].get<std::string>().size() > 40 ||
                !p["ts"].is_number_integer() || p["ts"].get<int64_t>() < 0 ||
                p["ts"].get<uint64_t>() > 9007199254740991ULL ||
                !p["checksum"].is_string() || !hexadecimal(p["checksum"], 64))
            throw Error("BAD_PACKET", "Invalid field types or values");
        std::string digest = p["checksum"];
        json unsigned_p = p; unsigned_p.erase("checksum");
        if (!equal_digest(digest, sha256(unsigned_p.dump())))
            throw Error("BAD_CHECKSUM", "Integrity check failed; packet rejected");
        return p;
    } catch (const Error&) { throw; }
    catch (const std::exception&) { throw Error("BAD_PACKET", "Malformed JSON or UTF-8"); }
}
bool read_exact(SOCKET sock, char* data, int size) {
    int offset = 0;
    while (offset < size) {
        int n = recv(sock, data + offset, size - offset, 0);
        if (n <= 0) return false;
        offset += n;
    }
    return true;
}
struct Peer {
    SOCKET sock;
    std::string name;  // Guarded by server state mutex.
    std::mutex write_mutex;
    std::atomic<bool> closed{false};
    std::deque<std::string> seen;
    std::deque<Clock::time_point> recent;
    explicit Peer(SOCKET s) : sock(s) {}
    ~Peer() { closesocket(sock); }
    bool send(const json& p) {
        std::string data = p.dump();
        if (data.size() > MAX_FRAME) throw Error("FRAME_TOO_LARGE", "Response exceeds maximum length");
        uint32_t size = htonl(uint32_t(data.size()));
        std::string frame((char*)&size, 4); frame += data;
        std::lock_guard<std::mutex> guard(write_mutex);
        if (closed) return false;
        size_t offset = 0;
        while (offset < frame.size()) {
            int n = ::send(sock, frame.data() + offset, int(frame.size() - offset), 0);
            if (n <= 0) return false;
            offset += n;
        }
        return true;
    }
};

class Server {
    std::mutex state, account_mutex, roster_mutex;
    std::map<std::string, std::shared_ptr<Peer>> users;
    std::set<std::shared_ptr<Peer>> peers;
    struct Pending { Clock::time_point deadline; json message; };
    std::map<std::pair<std::string, std::string>, Pending> pending;
    std::string room_id = hex(random_bytes(16));
    std::string db_path;
    json accounts = json::object();
    SOCKET listener = INVALID_SOCKET, udp = INVALID_SOCKET;
    sockaddr_in multicast{};
public:
    explicit Server(std::string path) : db_path(std::move(path)) {
        if (std::filesystem::exists(std::filesystem::u8path(db_path))) {
            std::ifstream in(std::filesystem::u8path(db_path));
            in >> accounts;
            if (!accounts.is_object()) throw std::runtime_error("Invalid account database");
        }
    }
    void run(const std::string& host, int port, const std::string& iface) {
        listener = socket(AF_INET, SOCK_STREAM, IPPROTO_TCP);
        sockaddr_in addr{}; addr.sin_family = AF_INET; addr.sin_port = htons((u_short)port);
        if (inet_pton(AF_INET, host.c_str(), &addr.sin_addr) != 1)
            throw std::runtime_error("Invalid listening IPv4");
        if (bind(listener, (sockaddr*)&addr, sizeof(addr)) != 0 || listen(listener, 32) != 0)
            throw std::runtime_error("Cannot bind/listen TCP port (already in use?)");
        udp = socket(AF_INET, SOCK_DGRAM, IPPROTO_UDP);
        DWORD ttl = 1; BOOL loop = TRUE;
        setsockopt(udp, IPPROTO_IP, IP_MULTICAST_TTL, (char*)&ttl, sizeof(ttl));
        setsockopt(udp, IPPROTO_IP, IP_MULTICAST_LOOP, (char*)&loop, sizeof(loop));
        in_addr outgoing{};
        if (inet_pton(AF_INET, iface.c_str(), &outgoing) != 1)
            throw std::runtime_error("Invalid multicast interface IPv4");
        if (setsockopt(udp, IPPROTO_IP, IP_MULTICAST_IF, (char*)&outgoing, sizeof(outgoing)) != 0)
            throw std::runtime_error("Cannot select multicast interface");
        multicast.sin_family = AF_INET; multicast.sin_port = htons(45861);
        inet_pton(AF_INET, "239.255.42.99", &multicast.sin_addr);
        std::thread([this] { repair(); }).detach();
        log("READY TCP " + host + ":" + std::to_string(port) + " | UDP 239.255.42.99:45861 | C++17");
        for (;;) {
            SOCKET sock = accept(listener, nullptr, nullptr);
            if (sock == INVALID_SOCKET) continue;
            auto peer = std::make_shared<Peer>(sock);
            DWORD timeout = 15000, send_timeout = 5000;
            setsockopt(sock, SOL_SOCKET, SO_RCVTIMEO, (char*)&timeout, sizeof(timeout));
            setsockopt(sock, SOL_SOCKET, SO_SNDTIMEO, (char*)&send_timeout, sizeof(send_timeout));
            {
                std::lock_guard<std::mutex> guard(state);
                if (peers.size() >= 64) continue;
                peers.insert(peer);
            }
            std::thread([this, peer] { serve(peer); }).detach();
        }
    }
private:
    void error(const std::shared_ptr<Peer>& p, const Error& e, const std::string& rid = "") {
        p->send(packet("ERROR", {{"code", e.code}, {"message", e.what()}, {"request", rid}}));
    }
    void serve(const std::shared_ptr<Peer>& peer) {
        try {
            while (!peer->closed) {
                uint32_t size;
                if (!read_exact(peer->sock, (char*)&size, 4)) break;
                size = ntohl(size);
                if (!size || size > MAX_FRAME) {
                    error(peer, Error("FRAME_TOO_LARGE", "TCP frame length must be 1..32768"));
                    break;
                }
                std::string raw(size, '\0');
                if (!read_exact(peer->sock, raw.data(), int(size))) break;
                std::string rid;
                try {
                    json p = parse(raw); rid = p["id"];
                    handle(peer, p);
                } catch (const Error& e) {
                    error(peer, e, rid);
                    log("REJECT " + e.code);
                } catch (const json::exception&) {
                    error(peer, Error("BAD_BODY", "Task body has invalid field types"), rid);
                }
            }
        } catch (const std::exception& e) { log(std::string("CONNECTION ERROR ") + e.what()); }
        drop(peer);
    }
    void save_accounts() {
        auto path = std::filesystem::u8path(db_path);
        if (path.has_parent_path()) std::filesystem::create_directories(path.parent_path());
        auto temporary = path; temporary += ".tmp";
        {
            std::ofstream out(temporary, std::ios::binary | std::ios::trunc);
            out << accounts.dump(2); out.flush();
            if (!out) throw std::runtime_error("Cannot write account database");
        }
        if (!MoveFileExW(temporary.c_str(), path.c_str(), MOVEFILE_REPLACE_EXISTING | MOVEFILE_WRITE_THROUGH))
            throw std::runtime_error("Cannot commit account database");
    }
    void handle(const std::shared_ptr<Peer>& peer, const json& p) {
        std::string task = p["type"], rid = p["id"];
        json body = p["body"];
        static const std::set<std::string> tasks{"REGISTER", "LOGIN", "LOGOUT", "MEMBERS", "CHAT", "ACK", "PING"};
        if (!tasks.count(task)) throw Error("INVALID_TASK", "Unknown task code: " + task);
        if (std::find(peer->seen.begin(), peer->seen.end(), rid) != peer->seen.end())
            throw Error("REPLAY", "Duplicate request identifier");
        peer->seen.push_back(rid); if (peer->seen.size() > 512) peer->seen.pop_front();
        auto now = Clock::now();
        while (!peer->recent.empty() && now - peer->recent.front() > std::chrono::seconds(1)) peer->recent.pop_front();
        if (peer->recent.size() >= 120) throw Error("RATE_LIMIT", "Too many requests");
        peer->recent.push_back(now);
        std::string name;
        { std::lock_guard<std::mutex> guard(state); name = peer->name; }
        if (task == "REGISTER" || task == "LOGIN") {
            if (!name.empty()) throw Error("STATE", "Logout before switching accounts");
            if (!body.contains("name") || !body["name"].is_string() || !body.contains("password") || !body["password"].is_string())
                throw Error("BAD_BODY", "name and password must be strings");
            std::string requested = body["name"], password = body["password"];
            if (!valid_name(requested) || codepoints(password).size() < 6 || codepoints(password).size() > 128)
                throw Error("BAD_BODY", "Name: 1..20 Chinese/ASCII letters/digits/_/-; password: 6..128 characters");
            if (task == "REGISTER") {
                std::lock_guard<std::mutex> guard(account_mutex);
                bool ok = !accounts.contains(requested);
                if (ok) {
                    auto salt = hex(random_bytes(16));
                    accounts[requested] = {{"salt", salt}, {"digest", derive(password, salt)}};
                    try { save_accounts(); }
                    catch (...) { accounts.erase(requested); throw; }
                }
                peer->send(packet("RESULT", {{"request", rid}, {"action", task}, {"ok", ok},
                    {"message", ok ? "注册成功，请登录" : "用户名已存在"}}));
                return;
            }
            bool ok = false;
            {
                std::lock_guard<std::mutex> guard(account_mutex);
                if (accounts.contains(requested)) {
                    const json& row = accounts[requested];
                    ok = equal_digest(derive(password, row.at("salt")), row.at("digest"));
                }
            }
            if (!ok) throw Error("AUTH_FAILED", "用户名或密码错误");
            {
                std::lock_guard<std::mutex> guard(state);
                if (users.count(requested)) throw Error("ALREADY_ONLINE", "该账号已经在线");
                peer->name = requested; users[requested] = peer;
            }
            peer->send(packet("RESULT", {{"request", rid}, {"action", task}, {"ok", true}, {"name", requested},
                  {"group", "239.255.42.99"}, {"udp_port", 45861}, {"room_id", room_id}, {"message", "登录成功"}}));
            log("LOGIN " + requested); roster(); return;
        }
        if (task == "PING") { peer->send(packet("PONG", {{"request", rid}})); return; }
        if (name.empty()) throw Error("NOT_LOGGED_IN", "请先登录");
        if (task == "LOGOUT") {
            {
                std::lock_guard<std::mutex> guard(state);
                users.erase(name); peer->name.clear();
                clear_pending(name);
            }
            peer->send(packet("RESULT", {{"request", rid}, {"action", task}, {"ok", true}, {"message", "已注销登录"}}));
            log("LOGOUT " + name); roster();
        } else if (task == "MEMBERS") { roster(); }
        else if (task == "ACK") {
            if (!body.contains("message_id") || !body["message_id"].is_string()) throw Error("BAD_BODY", "message_id must be a string");
            std::lock_guard<std::mutex> guard(state);
            pending.erase({name, body["message_id"].get<std::string>()});
        } else if (task == "CHAT") { chat(peer, body, rid, name); }
    }
    void chat(const std::shared_ptr<Peer>& sender, const json& body, const std::string& rid, const std::string& name) {
        if (!body.contains("text") || !body["text"].is_string() || !body.contains("mode") || !body["mode"].is_string())
            throw Error("BAD_BODY", "text and mode must be strings");
        std::string text = body["text"], mode = body["mode"];
        auto chars = codepoints(text);
        bool blank = chars.empty() || std::all_of(chars.begin(), chars.end(), [](unsigned c) {
            return c == 32 || (c >= 9 && c <= 13) || c == 0xa0 || c == 0x1680 ||
                   (c >= 0x2000 && c <= 0x200a) || c == 0x2028 || c == 0x2029 || c == 0x202f || c == 0x205f || c == 0x3000;
        });
        if (blank || chars.size() > 2000) throw Error("BAD_BODY", "消息须为 1 至 2000 个字符且不能全为空白");
        json targets = body.value("targets", json::array());
        if ((mode != "all" && mode != "selected") || !targets.is_array() || targets.size() > 64)
            throw Error("BAD_BODY", "Invalid mode or targets");
        std::set<std::string> requested;
        for (const auto& target : targets) {
            if (!target.is_string()) throw Error("BAD_BODY", "Recipient must be a string");
            requested.insert(target.get<std::string>());
        }
        std::vector<std::shared_ptr<Peer>> recipients;
        std::vector<std::string> names;
        json message;
        {
            std::lock_guard<std::mutex> guard(state);
            if (mode == "all") {
                if (!targets.empty()) throw Error("BAD_BODY", "Group message targets must be empty");
                for (const auto& entry : users) names.push_back(entry.first);
            } else {
                if (requested.empty()) throw Error("NO_RECIPIENT", "请选择在线接收人");
                for (const auto& target : requested) if (!users.count(target)) throw Error("NO_RECIPIENT", "接收人已离线");
                requested.insert(name); names.assign(requested.begin(), requested.end());
            }
            for (const auto& target : names) recipients.push_back(users.at(target));
            message = packet("MESSAGE", {{"room_id", room_id}, {"sender", name}, {"text", text}, {"mode", mode},
                           {"targets", targets}, {"recipients", names}, {"request", rid}});
            if (message.dump().size() > MAX_FRAME) throw Error("FRAME_TOO_LARGE", "Encoded message exceeds maximum length");
            if (mode == "all") for (const auto& target : names)
                pending[{target, message["id"].get<std::string>()}] = {Clock::now() + std::chrono::milliseconds(800), message};
        }
        if (mode == "all") {
            std::string data = message.dump();
            int sent = sendto(udp, data.data(), int(data.size()), 0, (sockaddr*)&multicast, sizeof(multicast));
            log("MULTICAST " + name + " -> " + std::to_string(names.size()) + " recipients, " +
                std::to_string(data.size()) + " bytes" + (sent < 0 ? " (failed; TCP repair pending)" : ""));
        } else {
            for (auto& peer : recipients) if (!peer->send(message)) drop(peer);
            log("SELECTED " + name + " -> " + targets.dump());
        }
        sender->send(packet("RESULT", {{"request", rid}, {"action", "CHAT"}, {"ok", true},
                                      {"message", "服务器已受理"}, {"message_id", message["id"]}}));
    }
    void clear_pending(const std::string& name) {  // Caller holds state mutex.
        for (auto it = pending.begin(); it != pending.end();)
            if (it->first.first == name) it = pending.erase(it); else ++it;
    }
    void drop(const std::shared_ptr<Peer>& peer) {
        if (peer->closed.exchange(true)) return;
        shutdown(peer->sock, SD_BOTH);
        bool changed;
        std::string name;
        {
            std::lock_guard<std::mutex> guard(state);
            name = peer->name; changed = !name.empty();
            if (changed) { users.erase(name); clear_pending(name); }
            peer->name.clear(); peers.erase(peer);
        }
        if (changed) { log("DISCONNECT " + name); roster(); }
    }
    void roster() {
        std::vector<std::shared_ptr<Peer>> failed;
        {
            std::lock_guard<std::mutex> serialize(roster_mutex);
            std::vector<std::string> names;
            std::vector<std::shared_ptr<Peer>> clients;
            {
                std::lock_guard<std::mutex> guard(state);
                for (const auto& entry : users) { names.push_back(entry.first); clients.push_back(entry.second); }
            }
            auto message = packet("ROSTER", {{"members", names}});
            for (auto& peer : clients) if (!peer->send(message)) failed.push_back(peer);
        }
        for (auto& peer : failed) drop(peer);
    }
    void repair() {
        for (;;) {
            std::this_thread::sleep_for(std::chrono::milliseconds(100));
            std::vector<std::pair<std::shared_ptr<Peer>, json>> due;
            {
                std::lock_guard<std::mutex> guard(state);
                for (auto it = pending.begin(); it != pending.end();) {
                    if (it->second.deadline <= Clock::now()) {
                        auto user = users.find(it->first.first);
                        if (user != users.end()) due.emplace_back(user->second, it->second.message);
                        it = pending.erase(it);
                    } else ++it;
                }
            }
            for (auto& entry : due) {
                if (!entry.first->send(entry.second)) drop(entry.first);
                log("TCP_REPAIR " + entry.second["id"].get<std::string>().substr(0, 8));
            }
        }
    }
};
int wmain(int argc, wchar_t** argv) {
    SetConsoleOutputCP(CP_UTF8);
    WSADATA wsa{};
    if (WSAStartup(MAKEWORD(2, 2), &wsa) != 0) return 1;
    try {
        std::string host = "0.0.0.0", iface = "0.0.0.0", db = "data/accounts.json";
        int port = 45860;
        std::vector<std::string> arguments;
        for (int i = 0; i < argc; ++i) {
            int size = WideCharToMultiByte(CP_UTF8, 0, argv[i], -1, nullptr, 0, nullptr, nullptr);
            std::string value(size, '\0');
            WideCharToMultiByte(CP_UTF8, 0, argv[i], -1, value.data(), size, nullptr, nullptr);
            value.pop_back(); arguments.push_back(value);
        }
        for (int i = 1; i < argc; ++i) {
            std::string arg = arguments[i];
            if (arg == "--help") { std::cout << "server.exe [--host IPv4] [--port N] [--interface IPv4] [--db PATH]\n"; return 0; }
            if (++i >= argc) throw std::runtime_error("Missing argument value");
            if (arg == "--host") host = arguments[i];
            else if (arg == "--port") port = std::stoi(arguments[i]);
            else if (arg == "--interface") iface = arguments[i];
            else if (arg == "--db") db = arguments[i];
            else throw std::runtime_error("Unknown option: " + arg);
        }
        if (port < 1 || port > 65535) throw std::runtime_error("Port must be 1..65535");
        Server server(db); server.run(host, port, iface);
    } catch (const std::exception& e) { std::cerr << "FATAL " << e.what() << std::endl; return 1; }
    return 0;
}
