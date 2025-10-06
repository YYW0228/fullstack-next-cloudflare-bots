#!/bin/bash

# 反向跟单机器人一键部署脚本
# 作者：游业伟反向跟单机器人项目
# 日期：2024年12月30日

echo "🚀 开始部署反向跟单机器人项目..."

# 设置项目目录
PROJECT_DIR="/Users/mac/Downloads/A本地知识库/youyewei2024.12.30"
cd "$PROJECT_DIR"

echo "📁 当前工作目录：$(pwd)"

# 第一步：检查并安装依赖
echo "🔧 第一步：检查Python环境和依赖..."

# 检查Python版本
python3 --version || {
    echo "❌ 请先安装Python 3.8+"
    exit 1
}

# 创建虚拟环境（如果不存在）
if [ ! -d "venv" ]; then
    echo "📦 创建Python虚拟环境..."
    python3 -m venv venv
fi

# 激活虚拟环境
echo "🔄 激活虚拟环境..."
source venv/bin/activate

# 安装依赖
echo "📥 安装项目依赖..."
pip install -r requirements.txt

# 第二步：数据库初始化
echo "🗃️ 第二步：初始化SQLite数据库..."

# 创建数据库初始化脚本
cat > init_database.py << 'EOF'
import sqlite3
import os
from datetime import datetime

def init_database():
    """初始化反向跟单机器人数据库"""
    db_path = "trading_bot.db"
    
    # 如果数据库已存在，备份
    if os.path.exists(db_path):
        backup_path = f"trading_bot_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db"
        os.rename(db_path, backup_path)
        print(f"📦 已备份现有数据库到: {backup_path}")
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # 创建信号表
    cursor.execute('''
    CREATE TABLE signals (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        signal_id TEXT UNIQUE NOT NULL,
        original_signal TEXT NOT NULL,
        parsed_data TEXT NOT NULL,
        signal_type TEXT NOT NULL,
        symbol TEXT NOT NULL,
        side TEXT NOT NULL,
        quantity REAL,
        price REAL,
        confidence REAL DEFAULT 0.5,
        source TEXT NOT NULL,
        received_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        processed_at TIMESTAMP,
        status TEXT DEFAULT 'pending'
    )
    ''')
    
    # 创建订单表
    cursor.execute('''
    CREATE TABLE orders (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        order_id TEXT UNIQUE NOT NULL,
        signal_id TEXT NOT NULL,
        exchange TEXT NOT NULL,
        symbol TEXT NOT NULL,
        side TEXT NOT NULL,
        type TEXT NOT NULL,
        quantity REAL NOT NULL,
        price REAL,
        status TEXT DEFAULT 'pending',
        exchange_order_id TEXT,
        filled_quantity REAL DEFAULT 0,
        avg_price REAL,
        commission REAL DEFAULT 0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (signal_id) REFERENCES signals (signal_id)
    )
    ''')
    
    # 创建持仓表
    cursor.execute('''
    CREATE TABLE positions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        symbol TEXT NOT NULL,
        exchange TEXT NOT NULL,
        side TEXT NOT NULL,
        quantity REAL NOT NULL,
        avg_price REAL NOT NULL,
        unrealized_pnl REAL DEFAULT 0,
        realized_pnl REAL DEFAULT 0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(symbol, exchange, side)
    )
    ''')
    
    # 创建交易统计表
    cursor.execute('''
    CREATE TABLE trading_stats (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        date TEXT NOT NULL,
        total_signals INTEGER DEFAULT 0,
        processed_signals INTEGER DEFAULT 0,
        successful_orders INTEGER DEFAULT 0,
        failed_orders INTEGER DEFAULT 0,
        total_pnl REAL DEFAULT 0,
        win_rate REAL DEFAULT 0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(date)
    )
    ''')
    
    # 创建配置表
    cursor.execute('''
    CREATE TABLE config (
        key TEXT PRIMARY KEY,
        value TEXT NOT NULL,
        description TEXT,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''')
    
    # 插入默认配置
    default_configs = [
        ('telegram_api_id', '', 'Telegram API ID'),
        ('telegram_api_hash', '', 'Telegram API Hash'),
        ('telegram_phone', '', 'Telegram Phone Number'),
        ('binance_api_key', '', 'Binance API Key'),
        ('binance_secret', '', 'Binance Secret Key'),
        ('risk_per_trade', '0.02', 'Risk per trade (2%)'),
        ('max_positions', '5', 'Maximum concurrent positions'),
        ('default_leverage', '1', 'Default leverage'),
        ('signal_confidence_threshold', '0.6', 'Minimum signal confidence'),
        ('reverse_mode', 'true', 'Enable reverse trading'),
        ('auto_trading', 'false', 'Enable automatic trading'),
    ]
    
    cursor.executemany('''
    INSERT OR IGNORE INTO config (key, value, description) VALUES (?, ?, ?)
    ''', default_configs)
    
    conn.commit()
    conn.close()
    
    print("✅ 数据库初始化完成！")
    print("📋 创建的表：signals, orders, positions, trading_stats, config")

if __name__ == "__main__":
    init_database()
EOF

# 运行数据库初始化
python init_database.py

# 第三步：配置文件创建
echo "⚙️ 第三步：创建配置文件..."

cat > config.json << 'EOF'
{
  "telegram": {
    "api_id": "",
    "api_hash": "",
    "phone": "",
    "channels": [
      "@trading_signals_channel1",
      "@trading_signals_channel2"
    ]
  },
  "exchanges": {
    "binance": {
      "api_key": "",
      "secret": "",
      "testnet": true,
      "base_url": "https://testnet.binance.vision"
    }
  },
  "trading": {
    "reverse_mode": true,
    "risk_per_trade": 0.02,
    "max_positions": 5,
    "default_leverage": 1,
    "auto_trading": false,
    "signal_confidence_threshold": 0.6
  },
  "logging": {
    "level": "INFO",
    "file": "trading_bot.log",
    "max_size_mb": 100,
    "backup_count": 5
  },
  "database": {
    "type": "sqlite",
    "path": "trading_bot.db"
  }
}
EOF

# 第四步：启动脚本
echo "🚀 第四步：创建启动脚本..."

cat > start_bot.sh << 'EOF'
#!/bin/bash

echo "🤖 启动反向跟单机器人..."

# 检查虚拟环境
if [ ! -d "venv" ]; then
    echo "❌ 虚拟环境不存在，请先运行部署脚本"
    exit 1
fi

# 激活虚拟环境
source venv/bin/activate

# 检查配置文件
if [ ! -f "config.json" ]; then
    echo "❌ 配置文件不存在，请先配置 config.json"
    exit 1
fi

# 检查数据库
if [ ! -f "trading_bot.db" ]; then
    echo "❌ 数据库不存在，请先运行数据库初始化"
    exit 1
fi

# 启动机器人
echo "🚀 启动交易机器人..."
python main.py

EOF

chmod +x start_bot.sh

# 第五步：配置检查脚本
echo "🔍 第五步：创建配置检查脚本..."

cat > check_config.py << 'EOF'
import json
import sqlite3
import os

def check_configuration():
    """检查项目配置状态"""
    print("🔍 检查项目配置状态...")
    
    issues = []
    
    # 检查配置文件
    if not os.path.exists('config.json'):
        issues.append("❌ config.json 文件不存在")
    else:
        try:
            with open('config.json', 'r') as f:
                config = json.load(f)
                
            # 检查关键配置
            if not config.get('telegram', {}).get('api_id'):
                issues.append("⚠️ Telegram API ID 未配置")
            if not config.get('telegram', {}).get('api_hash'):
                issues.append("⚠️ Telegram API Hash 未配置")
            if not config.get('exchanges', {}).get('binance', {}).get('api_key'):
                issues.append("⚠️ Binance API Key 未配置")
                
        except Exception as e:
            issues.append(f"❌ 配置文件格式错误: {e}")
    
    # 检查数据库
    if not os.path.exists('trading_bot.db'):
        issues.append("❌ 数据库文件不存在")
    else:
        try:
            conn = sqlite3.connect('trading_bot.db')
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = [row[0] for row in cursor.fetchall()]
            expected_tables = ['signals', 'orders', 'positions', 'trading_stats', 'config']
            
            for table in expected_tables:
                if table not in tables:
                    issues.append(f"❌ 数据库表 {table} 不存在")
            
            conn.close()
        except Exception as e:
            issues.append(f"❌ 数据库检查失败: {e}")
    
    # 检查依赖
    try:
        import ccxt
        import telethon
        import asyncio
        print("✅ 核心依赖库检查通过")
    except ImportError as e:
        issues.append(f"❌ 缺少依赖库: {e}")
    
    # 报告结果
    if not issues:
        print("🎉 配置检查完成，所有项目都正常！")
        print("📝 下一步：")
        print("   1. 编辑 config.json 填入您的API密钥")
        print("   2. 运行 ./start_bot.sh 启动机器人")
    else:
        print("❌ 发现以下问题：")
        for issue in issues:
            print(f"   {issue}")
        print("\n🔧 请解决这些问题后再次运行检查")

if __name__ == "__main__":
    check_configuration()
EOF

# 第六步：创建测试脚本
echo "🧪 第六步：创建测试脚本..."

cat > test_bot.py << 'EOF'
import asyncio
import json
import sqlite3
from datetime import datetime

async def test_signal_processing():
    """测试信号处理功能"""
    print("🧪 测试信号处理...")
    
    # 模拟信号
    test_signal = {
        "symbol": "BTCUSDT",
        "side": "BUY",
        "quantity": 0.001,
        "price": 45000,
        "confidence": 0.8,
        "source": "test",
        "timestamp": datetime.now().isoformat()
    }
    
    # 测试反向逻辑
    reverse_side = "SELL" if test_signal["side"] == "BUY" else "BUY"
    print(f"✅ 原始信号: {test_signal['side']} -> 反向信号: {reverse_side}")
    
    # 测试数据库写入
    try:
        conn = sqlite3.connect('trading_bot.db')
        cursor = conn.cursor()
        
        cursor.execute('''
        INSERT INTO signals (signal_id, original_signal, parsed_data, signal_type, 
                           symbol, side, quantity, price, confidence, source)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            f"test_{datetime.now().timestamp()}",
            json.dumps(test_signal),
            json.dumps(test_signal),
            "reverse",
            test_signal["symbol"],
            reverse_side,
            test_signal["quantity"],
            test_signal["price"],
            test_signal["confidence"],
            test_signal["source"]
        ))
        
        conn.commit()
        conn.close()
        print("✅ 数据库写入测试通过")
        
    except Exception as e:
        print(f"❌ 数据库测试失败: {e}")

def test_database():
    """测试数据库连接和基本操作"""
    print("🗃️ 测试数据库...")
    
    try:
        conn = sqlite3.connect('trading_bot.db')
        cursor = conn.cursor()
        
        # 测试查询
        cursor.execute("SELECT COUNT(*) FROM signals")
        signal_count = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM orders")
        order_count = cursor.fetchone()[0]
        
        print(f"✅ 数据库连接正常")
        print(f"📊 信号记录数: {signal_count}")
        print(f"📊 订单记录数: {order_count}")
        
        conn.close()
        
    except Exception as e:
        print(f"❌ 数据库测试失败: {e}")

if __name__ == "__main__":
    print("🧪 开始运行项目测试...")
    test_database()
    asyncio.run(test_signal_processing())
    print("✅ 测试完成！")
EOF

# 第七步：创建监控脚本
echo "📊 第七步：创建监控脚本..."

cat > monitor.py << 'EOF'
import sqlite3
import json
import time
from datetime import datetime, timedelta

def show_dashboard():
    """显示交易监控面板"""
    try:
        conn = sqlite3.connect('trading_bot.db')
        cursor = conn.cursor()
        
        print("\n" + "="*60)
        print("🤖 反向跟单机器人监控面板")
        print("="*60)
        
        # 今日统计
        today = datetime.now().strftime('%Y-%m-%d')
        
        cursor.execute("SELECT COUNT(*) FROM signals WHERE DATE(received_at) = ?", (today,))
        today_signals = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM orders WHERE DATE(created_at) = ?", (today,))
        today_orders = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM orders WHERE status = 'filled' AND DATE(created_at) = ?", (today,))
        today_filled = cursor.fetchone()[0]
        
        print(f"📅 今日统计 ({today})")
        print(f"   📡 接收信号: {today_signals}")
        print(f"   📋 生成订单: {today_orders}")
        print(f"   ✅ 成交订单: {today_filled}")
        
        # 最近信号
        print("\n📡 最近信号 (最新5条)")
        cursor.execute('''
        SELECT symbol, side, quantity, price, confidence, received_at, status 
        FROM signals 
        ORDER BY received_at DESC 
        LIMIT 5
        ''')
        
        signals = cursor.fetchall()
        if signals:
            for signal in signals:
                symbol, side, qty, price, conf, time, status = signal
                print(f"   {time[:19]} | {symbol} {side} {qty} @ {price} | 置信度:{conf:.2f} | {status}")
        else:
            print("   暂无信号记录")
        
        # 最近订单
        print("\n📋 最近订单 (最新5条)")
        cursor.execute('''
        SELECT symbol, side, quantity, price, status, created_at 
        FROM orders 
        ORDER BY created_at DESC 
        LIMIT 5
        ''')
        
        orders = cursor.fetchall()
        if orders:
            for order in orders:
                symbol, side, qty, price, status, time = order
                print(f"   {time[:19]} | {symbol} {side} {qty} @ {price} | {status}")
        else:
            print("   暂无订单记录")
        
        # 当前持仓
        print("\n💼 当前持仓")
        cursor.execute('SELECT symbol, side, quantity, avg_price, unrealized_pnl FROM positions WHERE quantity > 0')
        positions = cursor.fetchall()
        
        if positions:
            total_pnl = 0
            for pos in positions:
                symbol, side, qty, avg_price, pnl = pos
                total_pnl += pnl or 0
                print(f"   {symbol} {side} {qty} @ {avg_price} | PNL: {pnl:.4f}")
            print(f"   总计 PNL: {total_pnl:.4f}")
        else:
            print("   暂无持仓")
        
        print("="*60)
        print(f"⏰ 更新时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        conn.close()
        
    except Exception as e:
        print(f"❌ 监控面板错误: {e}")

def monitor_loop():
    """监控循环"""
    print("📊 启动实时监控 (按 Ctrl+C 退出)")
    
    try:
        while True:
            show_dashboard()
            time.sleep(30)  # 每30秒刷新一次
            
    except KeyboardInterrupt:
        print("\n👋 监控已停止")

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "loop":
        monitor_loop()
    else:
        show_dashboard()
EOF

# 完成部署
echo ""
echo "🎉 反向跟单机器人部署完成！"
echo ""
echo "📋 下一步操作："
echo "1. 配置API密钥: nano config.json"
echo "2. 检查配置: python check_config.py"
echo "3. 运行测试: python test_bot.py"
echo "4. 启动机器人: ./start_bot.sh"
echo "5. 监控状态: python monitor.py"
echo ""
echo "🔧 重要提醒："
echo "- 请在 config.json 中填入您的 Telegram 和交易所 API 密钥"
echo "- 建议先在测试网络上运行 (testnet: true)"
echo "- 确保风险控制参数符合您的需求"
echo ""
echo "📁 项目文件结构："
echo "├── main.py (主程序)"
echo "├── config.json (配置文件)"
echo "├── trading_bot.db (SQLite数据库)"
echo "├── start_bot.sh (启动脚本)"
echo "├── check_config.py (配置检查)"
echo "├── test_bot.py (测试脚本)"
echo "├── monitor.py (监控面板)"
echo "└── core-lib/ (核心库)"
echo ""
echo "✨ 祝您交易顺利！"