"""
测试DEX集成 - PING代币交易
Test DEX Integration for PING Token Trading
"""
import asyncio
import sys
from decimal import Decimal

from trading.dex import UniswapV4Client, get_token_config
from config.settings import settings


async def test_account_info():
    """测试1: 获取账户信息"""
    print("\n" + "="*60)
    print("📊 测试1: 获取账户信息")
    print("="*60)
    
    try:
        client = UniswapV4Client(
            private_key=settings.base_private_key,
            rpc_url=settings.base_rpc_url
        )
        
        account_info = await client.get_account_info()
        
        print(f"✅ 账户地址: {account_info['address']}")
        print(f"✅ ETH余额: {account_info['eth_balance']:.6f} ETH")
        print(f"✅ USDC余额: {account_info['usdc_balance']:.2f} USDC")
        
        # 检查余额是否足够
        if account_info['eth_balance'] < 0.001:
            print(f"⚠️  警告: ETH余额不足，建议至少 0.01 ETH用于Gas费")
            return False
            
        if account_info['usdc_balance'] < 10:
            print(f"⚠️  警告: USDC余额不足，建议至少 10 USDC用于测试交易")
            return False
        
        print(f"✅ 余额检查通过")
        return True
        
    except Exception as e:
        print(f"❌ 获取账户信息失败: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_token_balance():
    """测试2: 获取PING代币余额"""
    print("\n" + "="*60)
    print("📊 测试2: 获取PING代币余额")
    print("="*60)
    
    try:
        client = UniswapV4Client(
            private_key=settings.base_private_key,
            rpc_url=settings.base_rpc_url
        )
        
        # 获取PING配置
        ping_config = get_token_config("PING")
        ping_address = ping_config["address"]
        
        print(f"PING代币地址: {ping_address}")
        
        # 获取余额
        ping_balance = await client.get_token_balance(ping_address)
        
        print(f"✅ 当前PING余额: {ping_balance} PING")
        
        return True
        
    except Exception as e:
        print(f"❌ 获取PING余额失败: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_small_swap():
    """测试3: 小额交易（可选）"""
    print("\n" + "="*60)
    print("📊 测试3: 小额Swap测试（10 USDC -> PING）")
    print("="*60)
    
    # 确认用户是否要执行实际交易
    print("⚠️  这将执行真实交易！")
    print("   交易金额: 10 USDC")
    print("   目标代币: PING")
    print("   预计Gas费: ~0.0005 ETH")
    
    confirm = input("\n是否继续？(yes/no): ").strip().lower()
    
    if confirm != "yes":
        print("❌ 用户取消交易测试")
        return False
    
    try:
        client = UniswapV4Client(
            private_key=settings.base_private_key,
            rpc_url=settings.base_rpc_url
        )
        
        # 执行买入
        print("\n🔄 开始执行Swap...")
        result = await client.place_order(
            coin="PING",
            is_buy=True,
            sz=10,  # 10 USDC
        )
        
        if result.get("status") == "ok":
            print(f"✅ Swap成功!")
            print(f"   交易哈希: {result['tx_hash']}")
            print(f"   Gas消耗: {result['gas_used']}")
            print(f"   区块高度: {result['block_number']}")
            print(f"   浏览器: https://basescan.org/tx/{result['tx_hash']}")
            
            # 等待一下，然后检查新余额
            print("\n等待3秒后检查余额...")
            await asyncio.sleep(3)
            
            ping_config = get_token_config("PING")
            ping_balance = await client.get_token_balance(ping_config["address"])
            print(f"✅ 新的PING余额: {ping_balance} PING")
            
            return True
        else:
            print(f"❌ Swap失败: {result.get('message')}")
            return False
            
    except Exception as e:
        print(f"❌ Swap测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_get_positions():
    """测试4: 获取所有持仓"""
    print("\n" + "="*60)
    print("📊 测试4: 获取DEX持仓")
    print("="*60)
    
    try:
        client = UniswapV4Client(
            private_key=settings.base_private_key,
            rpc_url=settings.base_rpc_url
        )
        
        positions = await client.get_positions()
        
        if positions:
            print(f"✅ 找到 {len(positions)} 个持仓:")
            for pos in positions:
                print(f"   - {pos['coin']}: {pos['balance']:.6f}")
        else:
            print("ℹ️  当前无持仓（除稳定币外）")
        
        return True
        
    except Exception as e:
        print(f"❌ 获取持仓失败: {e}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    """主测试流程"""
    print("\n" + "="*60)
    print("🚀 DEX集成测试 - PING代币 (Base链)")
    print("="*60)
    
    # 检查配置
    if not settings.base_chain_enabled:
        print("❌ Base链未启用！")
        print("   请在.env中设置: BASE_CHAIN_ENABLED=True")
        return
    
    if not settings.base_private_key:
        print("❌ Base链私钥未配置！")
        print("   请在.env中设置: BASE_PRIVATE_KEY=0x...")
        return
    
    print(f"✅ Base链已启用")
    print(f"✅ RPC: {settings.base_rpc_url}")
    
    # 测试流程
    tests = [
        ("账户信息", test_account_info),
        ("代币余额", test_token_balance),
        ("持仓查询", test_get_positions),
    ]
    
    results = []
    
    for test_name, test_func in tests:
        try:
            success = await test_func()
            results.append((test_name, success))
        except KeyboardInterrupt:
            print("\n\n⚠️  用户中断测试")
            break
        except Exception as e:
            print(f"\n❌ 测试 {test_name} 异常: {e}")
            results.append((test_name, False))
    
    # 可选：小额交易测试
    print("\n" + "="*60)
    do_swap = input("是否执行小额交易测试？(yes/no): ").strip().lower()
    if do_swap == "yes":
        success = await test_small_swap()
        results.append(("小额交易", success))
    
    # 汇总结果
    print("\n" + "="*60)
    print("📊 测试结果汇总")
    print("="*60)
    
    for test_name, success in results:
        status = "✅ 通过" if success else "❌ 失败"
        print(f"{status} - {test_name}")
    
    total = len(results)
    passed = sum(1 for _, s in results if s)
    
    print(f"\n总计: {passed}/{total} 测试通过")
    
    if passed == total:
        print("\n🎉 所有测试通过！DEX集成就绪。")
    else:
        print(f"\n⚠️  有 {total - passed} 个测试失败，请检查配置和网络连接。")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n👋 测试被用户中断")
        sys.exit(0)

