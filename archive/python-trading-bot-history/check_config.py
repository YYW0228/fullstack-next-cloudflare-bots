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
