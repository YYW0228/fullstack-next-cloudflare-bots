# 🚀 macOS 快速启动指南

## 📊 当前状态
✅ **Python 环境**: 3.13.5 (完美支持)  
✅ **依赖包**: 全部已安装  
✅ **项目文件**: 结构完整  
✅ **权限设置**: 正常  
⚠️ **网络连接**: 需要在线环境运行  
⚠️ **API配置**: 需要填入真实密钥  

## 🔧 第一步：配置 API 密钥

### 1. 获取 Telegram API 密钥
访问 https://my.telegram.org/apps
- 登录您的 Telegram 账号
- 创建新应用获取 `api_id` 和 `api_hash`

### 2. 获取 OKX API 密钥
登录 OKX 交易所
- 进入 API 管理页面
- 创建新的 API 密钥（需要交易权限）
- 获取 `api_key`、`secret` 和 `passphrase`

### 3. 编辑配置文件

#### 简单机器人配置
```bash
# 编辑简单机器人配置
open -a TextEdit simple-reverse-bot/config/config.json
```

#### 海龟机器人配置  
```bash
# 编辑海龟机器人配置
open -a TextEdit turtle-reverse-bot/config/config.json
```

需要替换的字段：
```json
{
  "telegram": {
    "api_id": "YOUR_TELEGRAM_API_ID",          // 替换为真实值
    "api_hash": "YOUR_TELEGRAM_API_HASH",      // 替换为真实值  
    "phone_number": "YOUR_PHONE_NUMBER"        // 替换为真实值
  },
  "exchange": {
    "api_key": "YOUR_OKX_API_KEY",             // 替换为真实值
    "secret": "YOUR_OKX_SECRET",               // 替换为真实值
    "password": "YOUR_OKX_PASSWORD"            // 替换为真实值
  }
}
```

## 🧪 第二步：沙盒测试

### 启动简单机器人测试
```bash
# 确保在沙盒模式下测试
./start_simple_bot.sh
```

### 启动海龟机器人测试
```bash
# 海龟机器人测试
./start_turtle_bot.sh
```

### 查看日志
```bash
# 实时查看简单机器人日志
tail -f simple-reverse-bot/logs/bot.log

# 实时查看海龟机器人日志  
tail -f turtle-reverse-bot/logs/bot.log
```

## ⚡ 第三步：快速启动命令

### 一键启动 (推荐)
```bash
# 简单机器人 (30%固定止盈)
./start_simple_bot.sh

# 海龟机器人 (分层滚仓)
./start_turtle_bot.sh
```

### 后台运行
```bash
# 后台启动简单机器人
nohup ./start_simple_bot.sh > simple_bot.log 2>&1 &

# 后台启动海龟机器人
nohup ./start_turtle_bot.sh > turtle_bot.log 2>&1 &

# 查看进程
ps aux | grep python | grep main.py
```

### 停止机器人
```bash
# 如果在前台运行，直接 Ctrl+C

# 如果在后台运行，查找并停止进程
pkill -f "python.*main.py"

# 或者根据 PID 停止
kill <PID>
```

## 🔍 第四步：监控和调试

### 查看系统状态
```bash
# 检查机器人进程
ps aux | grep "python.*main.py"

# 查看网络连接
lsof -i | grep python

# 监控资源使用
top -pid $(pgrep -f "python.*main.py")
```

### 查看日志
```bash
# 查看最新日志
tail -f simple-reverse-bot/logs/bot.log
tail -f turtle-reverse-bot/logs/bot.log

# 查看历史日志
less simple-reverse-bot/logs/bot.log

# 搜索特定内容
grep "ERROR" simple-reverse-bot/logs/bot.log
grep "交易" turtle-reverse-bot/logs/bot.log
```

## 🎯 策略说明

### 简单反向机器人
- **策略**: 30% 固定止盈
- **逻辑**: 信号开多→我们开空，30%盈利即平仓
- **适合**: 稳健获利，快进快出

### 海龟反向机器人
- **策略**: 分层滚仓止盈
- **逻辑**: 递进反向加仓，分层止盈
- **适合**: 最大化收益，复杂策略

### 信号转换逻辑
```
原始信号 → 我们的操作
开多     → 开空
开空     → 开多  
平多     → 平空
平空     → 平多
```

## 🛡️ 安全建议

### 1. 配置安全
- 使用只读+交易权限的 API 密钥
- 不要给 API 密钥提现权限
- 定期更换 API 密钥

### 2. 资金安全
- 初始测试使用小资金
- 设置合理的风险参数
- 启用沙盒模式测试

### 3. 系统安全
- 定期备份配置文件
- 启用 macOS 防火墙
- 使用 FileVault 加密磁盘

## 🔧 常见问题解决

### 1. 权限问题
```bash
# 重置项目权限
sudo chown -R $(whoami) .
chmod +x *.sh
```

### 2. 网络问题
```bash
# 检查网络连接
ping google.com
ping api.telegram.org

# 检查防火墙设置
sudo /usr/libexec/ApplicationFirewall/socketfilterfw --getglobalstate
```

### 3. Python 环境问题
```bash
# 重建虚拟环境
rm -rf venv
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

## 📞 技术支持

### 自助诊断
```bash
# 运行环境检查
./check_macos_env.sh

# 查看详细错误
python simple-reverse-bot/main.py
```

### 日志分析
- ERROR 级别：需要立即处理的问题
- WARNING 级别：需要关注的异常
- INFO 级别：正常运行信息

---

## 🎉 快速启动流程总结

1. **配置 API** → 编辑 config.json 文件
2. **环境检查** → 运行 `./check_macos_env.sh`
3. **启动机器人** → 运行 `./start_simple_bot.sh`
4. **监控日志** → 运行 `tail -f */logs/bot.log`
5. **正常交易** → 等待信号并观察反向操作

**🎯 您的反向跟单机器人已经准备就绪！**