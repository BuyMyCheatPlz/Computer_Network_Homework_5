@echo off
chcp 65001 >nul
cd /d "%~dp0"
if not exist bin mkdir bin
where g++ >nul 2>nul
if errorlevel 1 (
  echo 请安装 MinGW-w64 并将 g++ 添加到 PATH，或使用 Visual Studio 开发者命令行：
  echo cl /std:c++17 /EHsc /utf-8 server_cpp\main.cpp /Fe:bin\chat_server.exe ws2_32.lib bcrypt.lib
  exit /b 1
)
g++ -std=c++17 -municode -O2 -Wall -Wextra -finput-charset=UTF-8 -fexec-charset=UTF-8 -static -static-libgcc -static-libstdc++ server_cpp\main.cpp -o bin\chat_server.exe -lws2_32 -lbcrypt
if errorlevel 1 exit /b 1
echo C++ 服务端编译完成：bin\chat_server.exe
