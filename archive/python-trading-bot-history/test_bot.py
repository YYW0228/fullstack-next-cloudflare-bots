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
