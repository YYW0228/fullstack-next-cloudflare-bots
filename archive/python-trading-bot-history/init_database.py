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
