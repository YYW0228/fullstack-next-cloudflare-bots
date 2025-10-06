#!/usr/bin/env python3
"""
OKX交易所配置助手
帮助配置和测试OKX API连接
"""

import json
import ccxt
import asyncio
from datetime import datetime

def create_okx_config_template():
    """创建OKX配置模板"""
    okx_config = {
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
            "okx": {
                "api_key": "",
                "secret": "",
                "passphrase": "",
                "sandbox": True,
                "base_url": "https://www.okx.com"
            }
        },
        "trading": {
            "reverse_mode": True,
            "risk_per_trade": 0.02,
            "max_positions": 5,
            "default_leverage": 1,
            "auto_trading": False,
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
    
    with open('config_okx.json', 'w', encoding='utf-8') as f:
        json.dump(okx_config, f, indent=2, ensure_ascii=False)
    
    print("✅ 已创建OKX配置模板: config_okx.json")
    print("")
    print("🔧 请填入以下信息：")
    print("1. OKX API密钥 (api_key, secret, passphrase)")
    print("2. Telegram API信息 (api_id, api_hash, phone)")
    print("3. 根据需要调整交易参数")
    print("")
    print("📝 OKX API申请地址: https://www.okx.com/account/my-api")

async def test_okx_connection(config_file='config.json'):
    """测试OKX连接"""
    try:
        with open(config_file, 'r', encoding='utf-8') as f:
            config = json.load(f)
        
        okx_config = config.get('exchanges', {}).get('okx', {})
        
        if not all([okx_config.get('api_key'), okx_config.get('secret'), okx_config.get('passphrase')]):
            print("❌ OKX API密钥信息不完整")
            return False
        
        # 创建OKX交易所实例
        exchange = ccxt.okx({
            'apiKey': okx_config['api_key'],
            'secret': okx_config['secret'],
            'password': okx_config['passphrase'],
            'sandbox': okx_config.get('sandbox', True),
            'enableRateLimit': True,
        })
        
        # 设置沙盒模式
        if okx_config.get('sandbox', True):
            exchange.set_sandbox_mode(True)
            print("🧪 使用沙盒模式")
        
        print("🔄 测试OKX连接...")
        
        # 测试账户信息
        balance = await exchange.fetch_balance()
        print("✅ OKX连接成功！")
        print(f"💰 账户余额: {balance.get('USDT', {}).get('free', 0)} USDT")
        
        # 测试市场数据
        ticker = await exchange.fetch_ticker('BTC/USDT')
        print(f"📊 BTC/USDT 价格: {ticker['last']}")
        
        return True
        
    except Exception as e:
        print(f"❌ OKX连接测试失败: {e}")
        return False

def show_okx_trading_pairs():
    """显示OKX支持的交易对"""
    try:
        exchange = ccxt.okx({
            'enableRateLimit': True,
        })
        
        markets = exchange.load_markets()
        
        # 筛选主要的USDT交易对
        usdt_pairs = [symbol for symbol in markets.keys() if symbol.endswith('/USDT') and markets[symbol]['active']]
        usdt_pairs.sort()
        
        print("🏪 OKX主要USDT交易对 (前20个):")
        for i, pair in enumerate(usdt_pairs[:20]):
            print(f"   {i+1:2d}. {pair}")
        
        print(f"\n📊 总计支持 {len(usdt_pairs)} 个USDT交易对")
        
    except Exception as e:
        print(f"❌ 获取交易对失败: {e}")

def update_config_for_okx():
    """更新现有配置文件支持OKX"""
    try:
        # 读取现有配置
        with open('config.json', 'r', encoding='utf-8') as f:
            config = json.load(f)
        
        # 备份原配置
        backup_file = f"config_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(backup_file, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
        print(f"📦 已备份原配置到: {backup_file}")
        
        # 更新为OKX配置
        config['exchanges'] = {
            "okx": {
                "api_key": "",
                "secret": "",
                "passphrase": "",
                "sandbox": True,
                "base_url": "https://www.okx.com"
            }
        }
        
        # 保存更新后的配置
        with open('config.json', 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
        
        print("✅ 已更新配置文件支持OKX")
        print("🔧 请填入您的OKX API密钥信息")
        
    except Exception as e:
        print(f"❌ 更新配置失败: {e}")

def main():
    """主菜单"""
    print("🤖 OKX交易所配置助手")
    print("=" * 50)
    print("1. 创建OKX配置模板")
    print("2. 测试OKX连接")
    print("3. 查看支持的交易对")
    print("4. 更新现有配置支持OKX")
    print("5. 退出")
    print("=" * 50)
    
    while True:
        choice = input("\n请选择操作 (1-5): ").strip()
        
        if choice == '1':
            create_okx_config_template()
        elif choice == '2':
            asyncio.run(test_okx_connection())
        elif choice == '3':
            show_okx_trading_pairs()
        elif choice == '4':
            update_config_for_okx()
        elif choice == '5':
            print("👋 再见！")
            break
        else:
            print("❌ 无效选择，请重新输入")

if __name__ == "__main__":
    main()