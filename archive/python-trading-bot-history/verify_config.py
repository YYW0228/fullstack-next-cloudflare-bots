#!/usr/bin/env python3
"""
配置验证器 - Linus级别的严谨性验证
为每一个配置项提供深度验证，确保系统的健壮性
"""

import json
import re
import sys
from pathlib import Path
from typing import Dict, List, Tuple, Any

class ConfigValidator:
    """配置验证器 - 零容忍的配置检查"""
    
    def __init__(self):
        self.errors = []
        self.warnings = []
        self.success_count = 0
        
    def validate_telegram_config(self, config: Dict) -> bool:
        """验证Telegram配置的完整性和正确性"""
        telegram = config.get('telegram', {})
        
        # API ID验证
        api_id = telegram.get('api_id')
        if not api_id or str(api_id).startswith('YOUR_'):
            self.errors.append("Telegram API ID 未配置或为占位符")
            return False
        
        try:
            api_id_int = int(api_id)
            if api_id_int <= 0:
                self.errors.append("Telegram API ID 必须为正整数")
                return False
        except ValueError:
            self.errors.append("Telegram API ID 格式不正确")
            return False
        
        # API Hash验证
        api_hash = telegram.get('api_hash')
        if not api_hash or api_hash.startswith('YOUR_'):
            self.errors.append("Telegram API Hash 未配置或为占位符")
            return False
        
        if len(api_hash) != 32:
            self.warnings.append("Telegram API Hash 长度通常为32字符")
        
        # 电话号码验证
        phone = telegram.get('phone_number')
        if not phone or phone.startswith('YOUR_'):
            self.errors.append("电话号码 未配置或为占位符")
            return False
        
        phone_pattern = r'^[\+]?[1-9][0-9]{7,15}$'
        if not re.match(phone_pattern, phone):
            self.warnings.append("电话号码格式可能不正确，请确认包含国际区号")
        
        self.success_count += 1
        return True
    
    def validate_okx_config(self, config: Dict) -> bool:
        """验证OKX交易所配置"""
        exchange = config.get('exchange', {})
        
        # API Key验证
        api_key = exchange.get('api_key')
        if not api_key or api_key.startswith('YOUR_'):
            self.errors.append("OKX API Key 未配置或为占位符")
            return False
        
        if len(api_key) < 20:
            self.warnings.append("OKX API Key 长度可能不正确")
        
        # Secret验证
        secret = exchange.get('secret')
        if not secret or secret.startswith('YOUR_'):
            self.errors.append("OKX Secret 未配置或为占位符")
            return False
        
        # Passphrase验证
        password = exchange.get('password')
        if not password or password.startswith('YOUR_'):
            self.errors.append("OKX Passphrase 未配置或为占位符")
            return False
        
        # 沙盒模式检查
        sandbox_mode = exchange.get('sandbox_mode', True)
        if not sandbox_mode:
            self.warnings.append("⚠️ 当前为实盘模式，请确保已充分测试")
        else:
            print("✅ 沙盒模式已启用，安全测试环境")
        
        self.success_count += 1
        return True
    
    def validate_risk_config(self, config: Dict) -> bool:
        """验证风险控制配置"""
        risk = config.get('risk', {})
        
        # 验证关键风险参数
        max_daily_loss = risk.get('max_daily_loss', 0)
        if max_daily_loss <= 0 or max_daily_loss > 0.2:
            self.warnings.append(f"每日最大亏损 {max_daily_loss*100}% 可能设置不当，建议1-10%")
        
        max_drawdown = risk.get('max_drawdown', 0)
        if max_drawdown <= 0 or max_drawdown > 0.5:
            self.warnings.append(f"最大回撤 {max_drawdown*100}% 可能设置不当，建议10-30%")
        
        max_position_size = risk.get('max_position_size', 0)
        if max_position_size <= 0:
            self.errors.append("最大仓位大小必须大于0")
            return False
        
        self.success_count += 1
        return True
    
    def validate_strategy_config(self, config: Dict) -> bool:
        """验证策略配置"""
        strategy = config.get('strategy', {})
        
        # 简单策略验证
        if config.get('bot_type') == 'simple_reverse':
            profit_target = strategy.get('profit_target', 0)
            if profit_target <= 0 or profit_target > 1:
                self.errors.append(f"止盈目标 {profit_target*100}% 设置不当，应为1-100%")
                return False
            
            stop_loss = strategy.get('stop_loss', 0)
            if stop_loss >= 0 or stop_loss < -0.5:
                self.errors.append(f"止损设置 {stop_loss*100}% 不当，应为负值且不超过-50%")
                return False
        
        # 海龟策略验证
        elif config.get('bot_type') == 'turtle_reverse':
            position_sizes = strategy.get('position_sizes', {})
            if not position_sizes or '1' not in position_sizes:
                self.errors.append("海龟策略缺少仓位大小配置")
                return False
            
            profit_thresholds = strategy.get('profit_thresholds', {})
            close_ratios = strategy.get('close_ratios', {})
            
            if not profit_thresholds or not close_ratios:
                self.errors.append("海龟策略缺少止盈配置")
                return False
        
        self.success_count += 1
        return True
    
    def validate_json_structure(self, file_path: str) -> Tuple[bool, Dict]:
        """验证JSON文件结构"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
            return True, config
        except json.JSONDecodeError as e:
            self.errors.append(f"{file_path}: JSON格式错误 - {str(e)}")
            return False, {}
        except FileNotFoundError:
            self.errors.append(f"{file_path}: 文件不存在")
            return False, {}
    
    def validate_config_file(self, file_path: str) -> bool:
        """验证单个配置文件"""
        print(f"\n🔍 验证配置文件: {file_path}")
        
        # JSON结构验证
        is_valid_json, config = self.validate_json_structure(file_path)
        if not is_valid_json:
            return False
        
        # 必需字段验证
        required_sections = ['telegram', 'exchange', 'trading', 'strategy', 'risk']
        missing_sections = [section for section in required_sections if section not in config]
        
        if missing_sections:
            self.errors.append(f"缺少必需配置节: {', '.join(missing_sections)}")
            return False
        
        # 详细配置验证
        validations = [
            self.validate_telegram_config(config),
            self.validate_okx_config(config),
            self.validate_risk_config(config),
            self.validate_strategy_config(config)
        ]
        
        return all(validations)
    
    def print_results(self):
        """打印验证结果"""
        print(f"\n{'='*50}")
        print(f"📊 配置验证结果")
        print(f"{'='*50}")
        
        if self.errors:
            print(f"\n❌ 发现 {len(self.errors)} 个错误:")
            for error in self.errors:
                print(f"   • {error}")
        
        if self.warnings:
            print(f"\n⚠️  发现 {len(self.warnings)} 个警告:")
            for warning in self.warnings:
                print(f"   • {warning}")
        
        if not self.errors:
            print(f"\n✅ 配置验证通过！")
            print(f"   验证通过的模块: {self.success_count}")
            print(f"   系统已准备就绪")
        else:
            print(f"\n🔧 请修复上述错误后重新验证")
        
        return len(self.errors) == 0

def main():
    """主验证流程"""
    validator = ConfigValidator()
    
    print("🔐 反向跟单机器人配置验证器")
    print("哥，让我以Linus级别的严谨性验证您的配置")
    
    config_files = [
        'simple-reverse-bot/config/config.json',
        'turtle-reverse-bot/config/config.json'
    ]
    
    all_valid = True
    for config_file in config_files:
        if Path(config_file).exists():
            if not validator.validate_config_file(config_file):
                all_valid = False
        else:
            print(f"⚠️ 配置文件不存在: {config_file}")
            all_valid = False
    
    # 打印最终结果
    success = validator.print_results()
    
    if success:
        print(f"\n🚀 下一步操作:")
        print(f"   ./start_simple_bot.sh  # 启动简单反向机器人")
        print(f"   ./start_turtle_bot.sh  # 启动海龟反向机器人")
        print(f"\n💡 监控命令:")
        print(f"   tail -f simple-reverse-bot/logs/bot.log")
        print(f"   tail -f turtle-reverse-bot/logs/bot.log")
    
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())