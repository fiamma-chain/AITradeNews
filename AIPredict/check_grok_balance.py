#!/usr/bin/env python3
"""快速检查Grok账户余额"""
import asyncio
import sys
from pathlib import Path

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent))

from config.settings import settings
from trading.hyperliquid.client import HyperliquidClient
from eth_account import Account


async def check_balance():
    """检查Grok账户余额"""
    print("=" * 60)
    print("🔍 检查Grok账户余额")
    print("=" * 60)
    print()
    
    # 获取Grok私钥
    private_key = settings.individual_grok_private_key
    
    if not private_key:
        print("❌ 错误: INDIVIDUAL_GROK_PRIVATE_KEY 未配置")
        return
    
    # 获取地址
    account = Account.from_key(private_key)
    address = account.address
    
    print(f"📍 Grok地址: {address}")
    print()
    
    # 检查Hyperliquid余额
    try:
        print("🔄 连接Hyperliquid...")
        hl_client = HyperliquidClient(private_key, testnet=settings.hyperliquid_testnet)
        
        account_info = await hl_client.get_account_info()
        
        if hasattr(account_info, 'get'):
            # 字典类型
            withdrawable = account_info.get('withdrawable', 0)
            account_value = account_info.get('accountValue', 0)
        else:
            # 对象类型
            withdrawable = getattr(account_info, 'withdrawable', 0)
            account_value = getattr(account_info, 'accountValue', 0)
        
        print("✅ Hyperliquid账户信息:")
        print(f"   可用余额: ${float(withdrawable):,.2f} USDT")
        print(f"   账户价值: ${float(account_value):,.2f} USDT")
        print()
        
        # 检查是否有持仓（如果客户端支持）
        try:
            if hasattr(hl_client, 'get_user_state'):
                user_state = await hl_client.get_user_state()
                positions = user_state.get('assetPositions', [])
                if positions:
                    print("📊 当前持仓:")
                    for pos in positions:
                        position_data = pos.get('position', {})
                        coin = position_data.get('coin', 'Unknown')
                        szi = float(position_data.get('szi', 0))
                        entry_price = float(position_data.get('entryPx', 0))
                        unrealized_pnl = float(position_data.get('unrealizedPnl', 0))
                        
                        if szi != 0:
                            side = "多头" if szi > 0 else "空头"
                            print(f"   {coin}: {side} {abs(szi):.4f}, 开仓价${entry_price:,.2f}, 浮盈${unrealized_pnl:,.2f}")
                else:
                    print("✅ 无持仓")
            else:
                print("✅ 无持仓（未检查）")
        except Exception as e:
            print(f"⚠️  持仓检查失败: {e}")
        
        print()
        
        # 风险提示
        if float(withdrawable) < 100:
            print("⚠️  警告: 余额不足100U，可能无法正常交易")
        elif float(withdrawable) < 200:
            print("⚠️  提示: 余额较低，建议充值至200U以上")
        else:
            print(f"✅ 余额充足 (${float(withdrawable):,.2f})")
        
        print()
        print("=" * 60)
        print("📋 消息交易配置:")
        print("=" * 60)
        print(f"保证金策略: 30%-100% (信心度决定)")
        print(f"杠杆范围: 10-50x (信心度决定)")
        print(f"止损: 1% (固定)")
        print(f"止盈: 5% (固定)")
        print()
        
        # 计算不同信心度的保证金
        balance = float(withdrawable)
        print("💰 不同信心度的保证金:")
        for confidence in [60, 70, 80, 90, 100]:
            if confidence < 60:
                margin_pct = 0.30
            else:
                margin_pct = 0.30 + ((confidence - 60) / 40) * 0.70
            
            margin = balance * margin_pct
            leverage = 10 + ((confidence - 60) / 40) * 40 if confidence >= 60 else 10
            position_value = margin * leverage
            
            print(f"   信心度{confidence}%: 保证金${margin:.2f} ({margin_pct*100:.0f}%), "
                  f"杠杆{leverage:.0f}x, 仓位${position_value:.0f}")
        
        print()
        print("=" * 60)
        
    except Exception as e:
        print(f"❌ 检查失败: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(check_balance())

