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
