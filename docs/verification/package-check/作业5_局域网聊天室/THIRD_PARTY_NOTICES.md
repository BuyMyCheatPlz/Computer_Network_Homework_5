# 第三方组件说明

1. JSON for Modern C++，nlohmann/json 3.11.3，作者 Niels Lohmann。
   固定版本源码：<https://github.com/nlohmann/json/tree/v3.11.3>。
   MIT 许可证原文随 `server_cpp/vendor/LICENSE.MIT` 提供，完整单头文件随源码提交。
2. 已编译服务端使用 MinGW-w64 GCC 16.1.0 的 C++ 标准运行库静态链接。
   GCC Runtime Library Exception：<https://www.gnu.org/licenses/gcc-exception-3.1.html>。
3. Python 客户端使用 Python 标准库与 Tcl/Tk，由用户本机 Python 安装提供。
4. 可选录像工具依赖 imageio-ffmpeg 0.6.0 提供的 FFmpeg。该媒体工具包未纳入提交归档，也不是聊天程序的运行依赖；如重新安装，按该工具包自带的许可证使用。
5. 报告基于用户提供的学校课程设计模板；原始模板不作修改，封面与教师评语页保留。
