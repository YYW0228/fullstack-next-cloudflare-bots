# -*- coding: utf-8 -*-

import asyncio
import time
from telethon import TelegramClient, events
import ccxt
import re
from datetime import datetime
import nest_asyncio
import logging
import pytz
import contextvars
import subprocess
import threading

# 配置异步支持
nest_asyncio.apply()
#----------------------------------------------日志部分---------------------------------------------
# 下单等相关重要信息记录到main7.log - main_logger
main_logger = logging.getLogger("main_logger")
if not main_logger.hasHandlers():
    main_logger.setLevel(logging.INFO)
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    file_handler = logging.FileHandler('main7.log', mode='a', encoding='utf-8')
    file_handler.setFormatter(formatter)
    main_logger.addHandler(file_handler)
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    main_logger.addHandler(console_handler)

console_logger = logging.getLogger("console_logger")
if not console_logger.hasHandlers():
    console_logger.setLevel(logging.INFO)
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(logging.Formatter('%(message)s'))
    console_logger.addHandler(console_handler)
#----------------------------------------------日志部分结束---------------------------------------------
#----------------------------------------------自行更改部分-------------------------------------------

# Telegram 配置 https://my.telegram.org/auth
api_id = '25626150'
api_hash = '29dcb630d6022f94085684a578bcddbe'
phone_number = '+8618605979375'

# 监听群组和发送消息频道 ID,跟单群 1001911467666
GROUP_IDS = [-1001911467666,]
CHANNEL_ID = -1002356209964          #返回消息机器人申请：https://teleme.io/articles/create_your_own_telegram_bot?hl=zh-hans
#----------------------实盘---------------------------------
okx = ccxt.okx({
    'apiKey': '845c1dfa-c68c-43fd-9190-2947692f048a',
    'secret': '21C8EDD2BE775BDC78ECBC07969242D9',
    'password': 'Asu3185818!',
    'enableRateLimit': True,
    'options': {
        'defaultType': 'swap'
    }
})

# 删除下面两端开启实盘
okx.set_sandbox_mode(True)
okx.headers.update({'x-simulated-trading': '1'})

#----------------------------------------------自行更改部分结束---------------------------------------------
# 获取余额
def get_balance():
    try:
        balance_info = okx.fetch_balance()
        return balance_info['total'].get('USDT', 0)
    except Exception as e:
        main_logger.error(f"获取余额失败: {e}")
        return 0

# 全局变量
symbol = 'BTC-USDT-SWAP'  # 定义交易对
paused = False   #机器人暂停
start_time = datetime.utcnow()  #启动时间
initial_balance = None  #初始化余额
leverage = 20 #默认20倍指令
last_open_price = None  #最后一次开仓价
trade_profit = 0   #盈利情况
conservative_mode = False  #保守模式（已阉割）
long_positions = []  # 存储多单记录
short_positions = []  # 存储空单记录
monitoring_task = None  # 实时监控任务
MAX_RETRIES = 5  # 多单市场监控任务最大重试次数、防止卡死，卡死后不做任何动作，优先监听信号
RETRY_DELAY = 2  # 多单市场监控任务每次重试的间隔（秒）、防止卡死，卡死后不做任何动作，优先监听信号
MAX_RETRIES_KONG = 5  # 空单市场监控任务最大重试次数（空单监控）
RETRY_DELAY_KONG = 2  # 空单市场监控任务每次重试的间隔（秒）（空单监控）
CONTROL_COMMANDS = ["暂停", "重启", "正常开单", "保守开单", "运行时间"]  #机器人支持的命令
china_timezone = pytz.timezone('Asia/Shanghai')  #北京时间
client = None  # 初始化全局 client 变量，用于发送消息
monitoring_long_positions = False  # 多单监控任务标志
monitoring_short_positions = False  # 空单监控任务标志
lock = threading.Lock() #减仓仓位锁


# ----------------------------------------------计算加权平均价格----------------------------------------------
def calculate_weighted_avg_price(positions, action=None):
    """
    计算加权平均价格。如果action是"减多仓"或"减空仓"，只更新数量，不计算加权价格。
    """
    # 如果是减仓操作，直接返回现有价格而不计算加权平均价格
    if action in ["减多仓", "减空仓"]:
        return None  # 可以返回其他默认值，或者保持当前价格不变

    # 过滤掉价格为 None 或已经平仓的仓位
    valid_positions = [pos for pos in positions if pos['price'] is not None and pos['quantity'] > 0]

    # 如果没有有效仓位，返回 None 或其他合适的默认值
    if not valid_positions:
        return None

    total_qty = sum(pos['quantity'] for pos in valid_positions)

    # 防止除以零
    if total_qty == 0:
        return None

    # 计算加权价格
    weighted_sum = sum(pos['price'] * pos['quantity'] for pos in valid_positions)
    return weighted_sum / total_qty

#----------------------------------------------减仓更新仓位、传递价格---------------------------------------------
def update_position_for_partial_closure(positions, quantity_to_close, action=None):
    """
    更新仓位时，减仓并且根据动作决定是否更新价格。
    如果动作为"减多仓"或"减空仓"，则只更新数量，价格不变。
    """
    remaining_qty_to_close = quantity_to_close
    updated_positions = []

    # 使用锁保护更新仓位的代码
    with lock:
        # 更新仓位数量6
        for pos in positions:
            if remaining_qty_to_close <= 0:
                updated_positions.append(pos)  # 如果减仓完成，直接加入剩余的仓位
                continue

            if pos['quantity'] > 0:
                if pos['quantity'] <= remaining_qty_to_close:
                    remaining_qty_to_close -= pos['quantity']
                    pos['quantity'] = 0  # 清空该仓位的数量
                else:
                    pos['quantity'] -= remaining_qty_to_close
                    remaining_qty_to_close = 0  # 减仓完成，退出循环

            updated_positions.append(pos)  # 更新后的仓位信息

        # 如果是"减多仓"或"减空仓"，不更新价格
        if action in ["减多仓", "减空仓"]:
            # 在这类操作下，我们假设仓位的价格信息不做改变
            pass

        # 计算更新后的仓位数量
        remaining_quantity = sum(pos['quantity'] for pos in updated_positions)

    # 返回更新后的仓位和当前剩余仓位数量
    return updated_positions, remaining_quantity

# --------------------------------------------------基本跟单功能---------------------------------------------------
async def place_order(client, symbol, action, amount):
    global initial_balance, long_positions, short_positions, paused, monitoring_long_positions, monitoring_short_positions
    if paused:  # 检查是否处于暂停状态
        main_logger.info("当前已暂停，跳过下单")
        return None
    try:
        side, posSide = {'开多': ('buy', 'long'), '平多': ('sell', 'long'),
                         '开空': ('sell', 'short'), '平空': ('buy', 'short')}.get(action, (None, None))

        if side is None:
            main_logger.warning(f"未识别的操作: {action}")
            return None

        # 执行下单操作
        order = okx.create_market_order(symbol, side, amount, params={'posSide': posSide})

        # 获取订单成交价格
        trade_price = order.get('price')
        if not trade_price:  # 如果价格为空
            # 尝试从订单详情中获取
            order_details = okx.fetch_order(order['id'], symbol)
            trade_price = order_details.get('average') or order_details.get('price')

        # 确保 trade_price 转换为 float
        if not trade_price:
            raise ValueError("无法获取订单成交价格")

        trade_price = float(trade_price)  # 将价格转为浮点数
        balance = get_balance()

        # 根据操作类型更新仓位
        if action == '开多':
            long_positions.append({'price': trade_price, 'quantity': amount})
            console_logger.info(f"记录多单开仓: {long_positions}")
        elif action == '开空':
            short_positions.append({'price': trade_price, 'quantity': amount})
            console_logger.info(f"记录空单开仓: {short_positions}")

        if initial_balance is None:
            initial_balance = balance

        balance_change = balance - initial_balance

        main_logger.info(f"下单成功: {order}")
        return {
            'timestamp': datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S'),
            'action': action,
            'amount': amount,
            'current_balance': balance,
            'balance_change': balance_change,
            'trade_price': trade_price
        }

    except Exception as e:
        error_message = str(e)
        if 'You don\'t have any positions in this contract that can be closed.' in error_message:
            # 检测到错误信息，清空相关仓位并停止下单
            if '平多' in action:
                main_logger.error(f"平多操作失败，未找到持仓，清空多单仓位记录")
                long_positions = []  # 清空多单仓位记录
                console_logger.info(f"已清空多单仓位记录: {long_positions}")
            elif '平空' in action:
                main_logger.error(f"平空操作失败，未找到持仓，清空空单仓位记录")
                short_positions = []  # 清空空单仓位记录
                console_logger.info(f"已清空空单仓位记录: {short_positions}")


            return None  # 返回 None 表示平仓失败，退出

        # 其他异常处理
        main_logger.error(f"下单时出错: {e}")
        return None



# 处理消息函数
async def handle_message(message, client):
    global leverage, paused, conservative_mode, long_positions, short_positions
    try:
        # 获取消息内容
        message_text = message.text.strip() if hasattr(message, 'text') else message.strip()
        # 记录原始信号
        main_logger.info(f"收到原始信号: {message_text}")
        # 删除"收到信号:"前缀，直接发送原始消息
        await client.send_message(CHANNEL_ID, message_text)

        # 如果程序已暂停，则跳过所有非控制命令的处理
        if paused and message_text not in CONTROL_COMMANDS:
            main_logger.info("当前已暂停，跳过非控制命令的处理")
            return

        # 处理控制命令
        if message_text in CONTROL_COMMANDS:
            # 使用 create_task 异步处理命令
            asyncio.create_task(handle_command(message_text, client))
            return

        # 处理倍数指令（如 "20倍"）
        if re.match(r'^\s*\d+\s*倍\s*$', message_text):
            leverage = int(re.search(r'\d+', message_text).group())
            main_logger.info(f"倍数设置: {leverage}倍")
            console_logger.info(f"倍数已更新为: {leverage}倍")
            await client.send_message(CHANNEL_ID, f"已设置倍数为: {leverage}倍")
            return

        # 修改交易信号匹配模式，使用更宽松的匹配方式
        pattern = r'\[(开空|平空|开多|平多)\]\s*数量:(\d+\.?\d*)\s*市场:([\w-]+)'
        match = re.search(pattern, message_text)

        if match:
            action = match.group(1)
            raw_quantity = float(match.group(2))
            symbol = match.group(3)

            # 记录信号解析结果
            main_logger.info(f"信号解析: 动作={action}, 原始数量={raw_quantity}, 市场={symbol}")

            # 创建一个异步任务来处理订单
            asyncio.create_task(process_order(action, raw_quantity, symbol, client))

        else:
            main_logger.warning(f"无效信号格式: {message_text}")
            console_logger.info("收到无效信号格式")
            
    except Exception as e:
        main_logger.error(f"信号处理异常: {str(e)}", exc_info=True)
        console_logger.error(f"处理错误: {str(e)}")

# 新增异步订单处理函数
async def process_order(action, raw_quantity, symbol, client):
    try:
        # 根据 raw_quantity 调整开仓或平仓的倍数
        if action in ["开多", "开空"]:
            # 开仓逻辑
            if raw_quantity == 1:
                adjusted_quantity = raw_quantity * 0
                main_logger.info(f"开多/开空，监听到数量为1，调整倍数为0倍，实际下单数量: {adjusted_quantity}")
            elif raw_quantity == 2:
                adjusted_quantity = raw_quantity * 0
                main_logger.info(f"开多/开空，监听到数量为2，调整倍数为0倍，实际下单数量: {adjusted_quantity}")
            elif raw_quantity == 3:
                adjusted_quantity = raw_quantity * 30
                main_logger.info(f"开多/开空，监听到数量为3，调整倍数为30倍，实际下单数量: {adjusted_quantity}")
            elif raw_quantity == 4:
                adjusted_quantity = raw_quantity * 40
                main_logger.info(f"开多/开空，监听到数量为4，调整倍数为40倍，实际下单数量: {adjusted_quantity}")
            elif raw_quantity == 5:
                adjusted_quantity = raw_quantity * 40
                main_logger.info(f"开多/开空，监听到数量为5，调整倍数为40倍，实际下单数量: {adjusted_quantity}")
            elif raw_quantity == 6:
                adjusted_quantity = raw_quantity * 40
                main_logger.info(f"开多/开空，监听到数量为6，调整倍数为40倍，实际下单数量: {adjusted_quantity}")
            else:
                adjusted_quantity = raw_quantity * leverage
                main_logger.info(f"开多/开空，监听到数量超过6，使用默认倍数 {leverage}，实际下单数量: {adjusted_quantity}")

        elif action in ["平多", "平空"]:
            # 平仓逻辑
            if raw_quantity == 1:
                adjusted_quantity = raw_quantity * 0
                main_logger.info(f"平多/平空，监听到数量为1，调整倍数为0倍，实际平仓数量: {adjusted_quantity}")
            elif raw_quantity == 2:
                adjusted_quantity = raw_quantity * 0
                main_logger.info(f"平多/平空，监听到数量为2，调整倍数为0倍，实际平仓数量: {adjusted_quantity}")
            elif raw_quantity == 3:
                adjusted_quantity = raw_quantity * 30
                main_logger.info(f"平多/平空，监听到数量为3，调整倍数为30倍，实际平仓数量: {adjusted_quantity}")
            elif raw_quantity == 4:
                adjusted_quantity = raw_quantity * 40
                main_logger.info(f"平多/平空，监听到数量为4，调整倍数为40倍，实际平仓数量: {adjusted_quantity}")
            elif raw_quantity == 5:
                adjusted_quantity = raw_quantity * 40
                main_logger.info(f"平多/平空，监听到数量为5，调整倍数为40倍，实际平仓数量: {adjusted_quantity}")
            elif raw_quantity == 6:
                adjusted_quantity = raw_quantity * 40
                main_logger.info(f"平多/平空，监听到数量为6，调整倍数为40倍，实际平仓数量: {adjusted_quantity}")
            else:
                adjusted_quantity = raw_quantity * 40
                main_logger.info(f"平多/平空，监听到数量超过6，使用默认倍数为40倍，实际平仓数量: {adjusted_quantity}")

        # 异步执行下单
        result = await place_order(client, symbol, action, adjusted_quantity)
        if result:
            main_logger.info(f"下单执行结果: {result}")
            console_logger.info(f"交易执行: {action} {adjusted_quantity}张 {symbol}")
            # 重置多单和空单的持仓
            if action == '平多':  # 如果是平多操作
                long_positions = []  # 重置多单持仓
                main_logger.info("平多后，已重置多单持仓信息。")
            elif action == '平空':  # 如果是平空操作
                short_positions = []  # 重置空单持仓
                main_logger.info("平空后，已重置空单持仓信息。")

    except Exception as e:
        main_logger.error(f"订单处理异常: {str(e)}")


# 处理控制命令
async def handle_command(command, client):
    global paused, conservative_mode
    if command == "暂停":
        paused = True
        await client.send_message(CHANNEL_ID, "已暂停交易")
        main_logger.info("已暂停交易")
    elif command == "重启":
        paused = False
        await client.send_message(CHANNEL_ID, "已重启交易")
        main_logger.info("已重启交易")
    elif command == "正常开单":
        conservative_mode = False
        await client.send_message(CHANNEL_ID, "已切换到正常开单模式")
        main_logger.info("切换到正常开单模式")
    elif command == "保守开单":
        conservative_mode = True
        await client.send_message(CHANNEL_ID, "已切换到保守开单模式")
        main_logger.info("切换到保守开单模式")
    elif command == "运行时间":
        elapsed_time = datetime.utcnow() - start_time
        current_balance = get_balance()
        balance_change = current_balance - initial_balance
        await client.send_message(
            CHANNEL_ID,
            f"机器人已运行时间: {elapsed_time}\n"
            f"初始余额: {initial_balance} USDT\n"
            f"当前余额: {current_balance} USDT\n"
            f"余额变动: {balance_change:.2f} USDT"
        )

#-------------------------------------------------------以上为原始代码---------------------------------------------
# 启动 Telegram 客户端监听
async def start_telegram_listener():
    global client
    async with TelegramClient('bot_session', api_id, api_hash) as client:
        # 监听新消息的事件处理器
        @client.on(events.NewMessage(chats=GROUP_IDS))
        async def message_handler(event):
            message = event.message.text
            main_logger.info(f"收到新消息: {message}")
            await handle_message(event.message, client)

        main_logger.info(f"开始监听群组: {GROUP_IDS}...")
        # 运行 Telegram 客户端事件循环
        await client.run_until_disconnected()

# 启动程序
async def main():
    global initial_balance
    initial_balance = get_balance()
    main_logger.info(f"程序启动，初始余额: {initial_balance}")


    telegram_task = asyncio.create_task(start_telegram_listener())  # 启动 Telegram 监听

    # 启动后台监控任务
    monitor_task_1 = asyncio.create_task(monitor_long_positions(symbol))  # 启动多单监控
    monitor_task_2 = asyncio.create_task(monitor_short_positions(symbol))  # 启动空单监控

    # 等待所有任务完成
    await asyncio.gather(telegram_task,monitor_task_1,monitor_task_2)

async def monitor_long_positions(symbol):
    """监控多单持仓"""
    global monitoring_long_positions
    retry_count = 0
    
    while True:
        try:
            if not monitoring_long_positions or not long_positions:
                await asyncio.sleep(2)
                continue

            # 获取当前市场价格
            ticker = okx.fetch_ticker(symbol)
            current_price = ticker['last']

            # 计算持仓的加权平均价格
            avg_price = calculate_weighted_avg_price(long_positions)
            
            if avg_price is None:
                await asyncio.sleep(2)
                continue

            # 计算盈亏百分比
            profit_percentage = ((current_price - avg_price) / avg_price) * 100

            main_logger.debug(f"多单监控 - 当前价格: {current_price}, 开仓均价: {avg_price}, 盈亏: {profit_percentage:.2f}%")
            
            # 重置重试计数
            retry_count = 0
            
            await asyncio.sleep(2)  # 每2秒检查一次

        except Exception as e:
            retry_count += 1
            main_logger.error(f"多单监控异常: {str(e)}")
            
            if retry_count >= MAX_RETRIES:
                main_logger.error("多单监控达到最大重试次数，暂停监控")
                monitoring_long_positions = False
                retry_count = 0
                
            await asyncio.sleep(RETRY_DELAY)

async def monitor_short_positions(symbol):
    """监控空单持仓"""
    global monitoring_short_positions
    retry_count = 0
    
    while True:
        try:
            if not monitoring_short_positions or not short_positions:
                await asyncio.sleep(2)
                continue

            # 获取当前市场价格
            ticker = okx.fetch_ticker(symbol)
            current_price = ticker['last']

            # 计算持仓的加权平均价格
            avg_price = calculate_weighted_avg_price(short_positions)
            
            if avg_price is None:
                await asyncio.sleep(2)
                continue

            # 计算盈亏百分比 (空单与多单计算方式相反)
            profit_percentage = ((avg_price - current_price) / avg_price) * 100

            main_logger.debug(f"空单监控 - 当前价格: {current_price}, 开仓均价: {avg_price}, 盈亏: {profit_percentage:.2f}%")
            
            # 重置重试计数
            retry_count = 0
            
            await asyncio.sleep(2)  # 每2秒检查一次

        except Exception as e:
            retry_count += 1
            main_logger.error(f"空单监控异常: {str(e)}")
            
            if retry_count >= MAX_RETRIES_KONG:
                main_logger.error("空单监控达到最大重试次数，暂停监控")
                monitoring_short_positions = False
                retry_count = 0
                
            await asyncio.sleep(RETRY_DELAY_KONG)

# 辅助函数：处理部分平仓逻辑
async def handle_partial_closure(symbol, positions, quantity, huoli, real_time_price, action, fraction):
    """
    处理部分平仓逻辑
    
    Args:
        symbol: 交易对
        positions: 持仓列表
        quantity: 平仓数量
        huoli: 获利比例
        real_time_price: 实时价格
        action: 交易动作（'多'或'空'）
        fraction: 平仓比例
    """
    global client

    retry_count = 0
    max_retries = 2

    while retry_count <= max_retries:
        try:
            # 计算平仓数量（保留一位小数）
            total_quantity = sum(pos['quantity'] for pos in positions)
            size_half = round(total_quantity * fraction, 1)
            remaining_quantity = size_half

            # 更新仓位信息
            positions, remaining_quantity = update_position_for_partial_closure(
                positions, 
                quantity_to_close=remaining_quantity, 
                action=f"减{action}仓"
            )

            # 执行平仓操作
            result = await place_order(client, symbol, f'平{action}', size_half)
            
            if result:
                main_logger.info(f"部分平{action}成功 - 数量: {size_half}, 获利: {huoli}%, 价格: {real_time_price}")
                console_logger.info(f"部分平{action}成功 - 数量: {size_half}")
                return True
            
            retry_count += 1
            await asyncio.sleep(1)

        except Exception as e:
            main_logger.error(f"部分平{action}操作时出错: {str(e)}")
            retry_count += 1
            if retry_count > max_retries:
                main_logger.error(f"部分平仓操作错误超过最大重试次数({max_retries})，退出")
                return False
            await asyncio.sleep(1)

    return False

# 辅助函数：处理完全平仓逻辑
async def handle_full_closure(symbol, positions, quantity, huoli, real_time_price, action):
    """
    处理完全平仓逻辑
    
    Args:
        symbol: 交易对
        positions: 持仓列表
        quantity: 平仓数量
        huoli: 获利比例
        real_time_price: 实时价格
        action: 交易动作（'多'或'空'）
    """
    global client, short_positions, long_positions
    
    total_quantity = sum(pos['quantity'] for pos in positions)
    retry_count = 0
    max_retries = 2

    while retry_count <= max_retries:
        try:
            # 执行完全平仓
            result = await place_order(client, symbol, f'平{action}', total_quantity)
            
            if result:
                main_logger.info(f"全部平{action}成功 - 数量: {total_quantity}, 获利: {huoli}%, 价格: {real_time_price}")
                console_logger.info(f"全部平{action}成功 - 数量: {total_quantity}")
                
                # 清空对应的仓位记录
                if action == '多':
                    long_positions = []
                    main_logger.info("已清空多单仓位记录")
                else:
                    short_positions = []
                    main_logger.info("已清空空单仓位记录")
                    
                return True

            retry_count += 1
            await asyncio.sleep(1)

        except Exception as e:
            if 'You don\'t have any positions in this contract that can be closed.' in str(e):
                main_logger.error(f"{action}操作失败，未找到持仓，清空对应仓位记录")
                
                if action == '多':
                    long_positions = []
                    main_logger.info(f"已清空多单仓位记录: {long_positions}")
                else:
                    short_positions = []
                    main_logger.info(f"已清空空单仓位记录: {short_positions}")
                
                return False

            main_logger.error(f"全部平{action}操作时出错: {str(e)}")
            retry_count += 1
            if retry_count > max_retries:
                main_logger.error(f"全部平仓操作错误超过最大重试次数({max_retries})，退出")
                return False
            await asyncio.sleep(1)

    return False

# 启动事件循环
if __name__ == '__main__':
    asyncio.run(main())  # 使用 asyncio.run() 启动事件循环
