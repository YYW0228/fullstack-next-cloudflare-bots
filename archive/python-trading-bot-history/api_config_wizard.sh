#!/bin/bash
# API配置向导 - 为Linus级别的严谨性而设计

echo "🔐 反向跟单机器人 API 配置向导"
echo "=================================="
echo "哥，我将帮您安全地配置API密钥"
echo ""

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# 验证函数
validate_not_empty() {
    local value="$1"
    local field="$2"
    if [ -z "$value" ] || [ "$value" = "YOUR_"* ]; then
        echo -e "${RED}❌ $field 不能为空或包含占位符${NC}"
        return 1
    fi
    return 0
}

validate_phone() {
    local phone="$1"
    if [[ ! "$phone" =~ ^[\+]?[1-9][0-9]{7,15}$ ]]; then
        echo -e "${YELLOW}⚠️  电话号码格式可能不正确，请确认${NC}"
    fi
}

# 收集API信息
echo -e "${BLUE}📱 Telegram API 配置${NC}"
echo "请访问 https://my.telegram.org/apps 获取API信息"
echo ""

read -p "请输入 Telegram API ID: " telegram_api_id
validate_not_empty "$telegram_api_id" "Telegram API ID" || exit 1

read -p "请输入 Telegram API Hash: " telegram_api_hash
validate_not_empty "$telegram_api_hash" "Telegram API Hash" || exit 1

read -p "请输入手机号码 (含国际区号，如+8613800138000): " phone_number
validate_not_empty "$phone_number" "手机号码" || exit 1
validate_phone "$phone_number"

echo ""
echo -e "${BLUE}🏦 OKX 交易所 API 配置${NC}"
echo "请确保API密钥具有交易权限，但不要给予提现权限"
echo ""

read -p "请输入 OKX API Key: " okx_api_key
validate_not_empty "$okx_api_key" "OKX API Key" || exit 1

read -s -p "请输入 OKX Secret (输入时不显示): " okx_secret
echo ""
validate_not_empty "$okx_secret" "OKX Secret" || exit 1

read -s -p "请输入 OKX Passphrase (输入时不显示): " okx_password
echo ""
validate_not_empty "$okx_password" "OKX Passphrase" || exit 1

echo ""
echo -e "${BLUE}⚙️  交易模式选择${NC}"
echo "1) 沙盒模式 (推荐首次使用)"
echo "2) 实盘模式 (确认配置无误后使用)"
read -p "请选择模式 (1/2): " mode_choice

sandbox_mode="true"
if [ "$mode_choice" = "2" ]; then
    echo -e "${YELLOW}⚠️  您选择了实盘模式，请确保已充分测试${NC}"
    read -p "确认使用实盘模式? (yes/no): " confirm
    if [ "$confirm" = "yes" ]; then
        sandbox_mode="false"
    else
        echo "已设置为沙盒模式"
        sandbox_mode="true"
    fi
fi

# 配置简单机器人
echo ""
echo -e "${GREEN}🤖 配置简单反向机器人...${NC}"

cat > simple-reverse-bot/config/config.json << EOF
{
  "description": "简单反向机器人配置 - 30%固定止盈策略",
  "bot_type": "simple_reverse",
  "version": "1.0.0",
  
  "telegram": {
    "api_id": "$telegram_api_id",
    "api_hash": "$telegram_api_hash", 
    "phone_number": "$phone_number",
    "group_ids": [-1001911467666],
    "channel_id": -1002356209964,
    "session_name": "simple_reverse_bot"
  },
  
  "exchange": {
    "name": "okx",
    "api_key": "$okx_api_key",
    "secret": "$okx_secret",
    "password": "$okx_password",
    "sandbox_mode": $sandbox_mode,
    "enable_rate_limit": true,
    "default_type": "swap",
    "timeout": 30,
    "max_retries": 3
  },
  
  "trading": {
    "symbol": "BTC-USDT-SWAP",
    "market_order_only": true,
    "fast_execution": true,
    "max_slippage": 0.002,
    "min_order_amount": 0.01
  },
  
  "strategy": {
    "name": "SimpleReverse",
    "description": "30%固定止盈反向跟单策略",
    "profit_target": 0.30,
    "stop_loss": -0.15,
    "position_timeout_hours": 6,
    "max_concurrent_positions": 5,
    "base_position_size": 10,
    "max_position_size": 100,
    "min_signal_confidence": 0.3,
    "price_update_interval": 3,
    "enabled_signal_quantities": [1, 2, 3, 4, 5, 6, 7, 8]
  },
  
  "risk": {
    "max_daily_loss": 0.05,
    "max_position_size": 500.0,
    "max_drawdown": 0.20,
    "emergency_stop_loss": 0.15,
    "max_daily_trades": 50,
    "account_risk_percentage": 0.02
  },
  
  "monitoring": {
    "check_interval": 3,
    "price_update_interval": 2,
    "status_report_interval": 300,
    "performance_window_hours": 24,
    "alert_thresholds": {
      "high_loss": 0.05,
      "position_timeout": 21600,
      "api_error_rate": 0.1,
      "consecutive_losses": 5
    }
  },
  
  "logging": {
    "level": "INFO",
    "console_output": true,
    "file_output": true,
    "max_file_size": "10MB",
    "backup_count": 5,
    "structured_logging": true
  },
  
  "system": {
    "timezone": "UTC", 
    "locale": "zh_CN",
    "max_memory_usage": "512MB",
    "graceful_shutdown_timeout": 30
  }
}
EOF

# 配置海龟机器人
echo -e "${GREEN}🐢 配置海龟反向机器人...${NC}"

cat > turtle-reverse-bot/config/config.json << EOF
{
  "description": "海龟反向机器人配置 - 滚仓分层止盈策略",
  "bot_type": "turtle_reverse",
  "version": "1.0.0",
  
  "telegram": {
    "api_id": "$telegram_api_id",
    "api_hash": "$telegram_api_hash",
    "phone_number": "$phone_number", 
    "group_ids": [-1001911467666],
    "channel_id": -1002356209964,
    "session_name": "turtle_reverse_bot"
  },
  
  "exchange": {
    "name": "okx",
    "api_key": "$okx_api_key",
    "secret": "$okx_secret", 
    "password": "$okx_password",
    "sandbox_mode": $sandbox_mode,
    "enable_rate_limit": true,
    "default_type": "swap",
    "timeout": 30,
    "max_retries": 3
  },
  
  "trading": {
    "symbol": "BTC-USDT-SWAP",
    "market_order_only": true,
    "fast_execution": true,
    "max_slippage": 0.002,
    "min_order_amount": 0.01
  },
  
  "strategy": {
    "name": "TurtleReverse",
    "description": "海龟滚仓分层止盈反向跟单策略",
    
    "position_sizes": {
      "1": 10,
      "2": 20, 
      "3": 30,
      "4": 40,
      "5": 50,
      "6": 60,
      "7": 70,
      "8": 80
    },
    
    "profit_thresholds": {
      "1": 0.0,
      "2": 0.0,
      "3": 0.50,
      "4": 0.30,
      "5": 0.30,
      "6": 0.30,
      "7": 0.30,
      "8": 0.30
    },
    
    "close_ratios": {
      "1": 0.0,
      "2": 0.0, 
      "3": 0.50,
      "4": 0.80,
      "5": 0.90,
      "6": 0.90,
      "7": 0.90,
      "8": 1.00
    },
    
    "sequence_timeout_hours": 8,
    "emergency_stop_loss": -0.20,
    "max_concurrent_sequences": 3,
    "min_signal_confidence": 0.6,
    "sequence_cooldown_minutes": 30,
    "max_sequence_duration_hours": 12
  },
  
  "risk": {
    "max_daily_loss": 0.08,
    "max_position_size": 1000.0,
    "max_drawdown": 0.25,
    "max_sequence_size": 800.0,
    "emergency_stop_loss": 0.20,
    "max_daily_trades": 100,
    "account_risk_percentage": 0.03,
    "sequence_risk_limit": 0.15
  },
  
  "monitoring": {
    "check_interval": 2,
    "price_update_interval": 2,
    "sequence_check_interval": 10,
    "status_report_interval": 180,
    "performance_window_hours": 24,
    "alert_thresholds": {
      "high_loss": 0.08,
      "sequence_timeout": 28800,
      "api_error_rate": 0.1,
      "high_risk_sequences": 2,
      "emergency_drawdown": 0.18
    }
  },
  
  "advanced": {
    "dynamic_position_sizing": true,
    "confidence_based_sizing": true,
    "volatility_adjustment": true,
    "trend_confirmation": false,
    "partial_profit_optimization": true,
    "smart_sequence_management": true
  },
  
  "logging": {
    "level": "INFO",
    "console_output": true,
    "file_output": true,
    "max_file_size": "20MB",
    "backup_count": 10,
    "structured_logging": true,
    "sequence_logging": true,
    "trade_logging": true
  },
  
  "system": {
    "timezone": "UTC",
    "locale": "zh_CN", 
    "max_memory_usage": "1GB",
    "graceful_shutdown_timeout": 60,
    "emergency_shutdown_conditions": {
      "max_loss_percentage": 0.25,
      "consecutive_failed_orders": 10,
      "api_error_threshold": 0.20
    }
  }
}
EOF

# 验证配置
echo ""
echo -e "${GREEN}✅ API配置完成！${NC}"
echo ""
echo -e "${BLUE}📊 配置验证：${NC}"

# 验证JSON格式
if python3 -c "import json; json.load(open('simple-reverse-bot/config/config.json'))" 2>/dev/null; then
    echo -e "✅ 简单机器人配置 - ${GREEN}JSON格式正确${NC}"
else
    echo -e "❌ 简单机器人配置 - ${RED}JSON格式错误${NC}"
fi

if python3 -c "import json; json.load(open('turtle-reverse-bot/config/config.json'))" 2>/dev/null; then
    echo -e "✅ 海龟机器人配置 - ${GREEN}JSON格式正确${NC}"
else
    echo -e "❌ 海龟机器人配置 - ${RED}JSON格式错误${NC}"
fi

# 安全提醒
echo ""
echo -e "${YELLOW}🔒 安全提醒：${NC}"
echo "   - API密钥已保存到配置文件中"
echo "   - 请确保API密钥只有交易权限，没有提现权限"
echo "   - 配置文件包含敏感信息，请妥善保管"
echo "   - 当前模式: $([ "$sandbox_mode" = "true" ] && echo "沙盒模式 (安全)" || echo "实盘模式 (注意风险)")"

echo ""
echo -e "${GREEN}🚀 下一步：${NC}"
echo "   运行: ./start_simple_bot.sh"
echo "   或者: ./start_turtle_bot.sh"