# macOS 反向跟单机器人部署指南

## 🍎 macOS 环境准备

### 1. 检查 Python 环境
```bash
# 检查 Python 版本 (需要 3.8+)
python3 --version

# 检查 pip
pip3 --version
```

### 2. 创建和激活虚拟环境
```bash
# 创建虚拟环境
python3 -m venv venv

# 激活虚拟环境 (macOS/Linux)
source venv/bin/activate

# 验证虚拟环境
which python
```

### 3. 安装核心库和依赖
```bash
# 安装核心库
cd core-lib && pip install -e . && cd ..

# 安装其他依赖
pip install -r requirements.txt
```

## 🚀 macOS 启动脚本

### 简单机器人启动脚本
创建 `start_simple_bot.sh`:
```bash
#!/bin/bash
echo "🤖 启动简单反向机器人..."

# 检查虚拟环境
if [ ! -d "venv" ]; then
    echo "创建虚拟环境..."
    python3 -m venv venv
fi

# 激活虚拟环境
source venv/bin/activate

# 安装依赖
echo "检查依赖..."
cd core-lib && pip install -e . && cd ..

# 启动简单机器人
echo "启动简单反向机器人..."
cd simple-reverse-bot
python main.py
```

### 海龟机器人启动脚本
创建 `start_turtle_bot.sh`:
```bash
#!/bin/bash
echo "🐢 启动海龟反向机器人..."

# 检查虚拟环境
if [ ! -d "venv" ]; then
    echo "创建虚拟环境..."
    python3 -m venv venv
fi

# 激活虚拟环境
source venv/bin/activate

# 安装依赖
echo "检查依赖..."
cd core-lib && pip install -e . && cd ..

# 启动海龟机器人
echo "启动海龟反向机器人..."
cd turtle-reverse-bot
python main.py
```

## 🔒 macOS 权限设置

### 1. 脚本执行权限
```bash
# 给启动脚本添加执行权限
chmod +x start_simple_bot.sh
chmod +x start_turtle_bot.sh
```

### 2. 网络权限
- 首次运行时，macOS 可能会询问网络访问权限
- 请选择"允许"以确保机器人能连接到交易所和Telegram

### 3. 防火墙设置
```bash
# 检查防火墙状态
sudo /usr/libexec/ApplicationFirewall/socketfilterfw --getglobalstate

# 如果需要，允许Python网络连接
# 系统偏好设置 -> 安全性与隐私 -> 防火墙 -> 防火墙选项
```

## 📱 macOS 后台运行

### 使用 launchd 服务 (推荐)
创建 `~/Library/LaunchAgents/com.rovodev.simple-bot.plist`:
```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.rovodev.simple-bot</string>
    <key>ProgramArguments</key>
    <array>
        <string>/bin/bash</string>
        <string>/path/to/your/project/start_simple_bot.sh</string>
    </array>
    <key>WorkingDirectory</key>
    <string>/path/to/your/project</string>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
    <key>StandardErrorPath</key>
    <string>/tmp/simple-bot.err</string>
    <key>StandardOutPath</key>
    <string>/tmp/simple-bot.out</string>
</dict>
</plist>
```

### 管理 launchd 服务
```bash
# 加载服务
launchctl load ~/Library/LaunchAgents/com.rovodev.simple-bot.plist

# 启动服务
launchctl start com.rovodev.simple-bot

# 停止服务
launchctl stop com.rovodev.simple-bot

# 卸载服务
launchctl unload ~/Library/LaunchAgents/com.rovodev.simple-bot.plist
```

## 🔍 macOS 调试和监控

### 1. 查看日志
```bash
# 查看系统日志
tail -f /var/log/system.log | grep "rovodev"

# 查看应用日志
tail -f simple-reverse-bot/logs/bot.log
tail -f turtle-reverse-bot/logs/bot.log
```

### 2. 监控进程
```bash
# 查看Python进程
ps aux | grep python

# 监控资源使用
top -p $(pgrep -f "python.*main.py")
```

### 3. 网络监控
```bash
# 监控网络连接
netstat -an | grep ESTABLISHED | grep python
lsof -i | grep python
```

## ⚠️ macOS 常见问题和解决方案

### 1. SSL 证书问题
```bash
# 更新证书
/Applications/Python\ 3.x/Install\ Certificates.command
```

### 2. 权限问题
```bash
# 重置权限
sudo chown -R $(whoami) /path/to/project
chmod -R 755 /path/to/project
```

### 3. 端口占用
```bash
# 查找占用端口的进程
lsof -i :8080
sudo kill -9 <PID>
```

### 4. 虚拟环境问题
```bash
# 重新创建虚拟环境
rm -rf venv
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

## 🎯 macOS 优化建议

### 1. 性能优化
- 关闭不必要的后台应用
- 设置"节能器"为"从不"（如果插电使用）
- 监控内存使用情况

### 2. 稳定性优化
- 定期重启机器人
- 设置自动备份配置
- 使用 SSD 存储提高 I/O 性能

### 3. 安全优化
- 启用 FileVault 磁盘加密
- 定期更新 macOS
- 使用强密码保护 API 密钥

## 🚀 快速启动 (macOS)

```bash
# 一键启动简单机器人
./start_simple_bot.sh

# 一键启动海龟机器人  
./start_turtle_bot.sh

# 后台启动并查看日志
nohup ./start_simple_bot.sh > simple_bot.log 2>&1 &
tail -f simple_bot.log
```