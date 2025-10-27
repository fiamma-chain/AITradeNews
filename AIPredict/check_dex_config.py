"""
检查DEX配置
Check DEX Configuration
"""
from config.settings import settings
from trading.dex import get_token_config, BASE_CONFIG


def check_dex_config():
    """检查DEX配置是否完整"""
    print("\n" + "="*60)
    print("🔍 DEX配置检查")
    print("="*60)
    
    issues = []
    
    # 1. 检查Base链是否启用
    print(f"\n1️⃣  Base链状态")
    if settings.base_chain_enabled:
        print(f"   ✅ Base链已启用")
    else:
        print(f"   ⚠️  Base链未启用")
        issues.append("需要在.env中设置: BASE_CHAIN_ENABLED=True")
    
    # 2. 检查RPC URL
    print(f"\n2️⃣  RPC配置")
    print(f"   RPC URL: {settings.base_rpc_url}")
    if "mainnet.base.org" in settings.base_rpc_url:
        print(f"   ✅ 使用Base主网")
    else:
        print(f"   ℹ️  使用自定义RPC")
    
    # 3. 检查私钥
    print(f"\n3️⃣  私钥配置")
    if settings.base_private_key and len(settings.base_private_key) > 10:
        # 隐藏私钥，只显示前缀和长度
        masked = settings.base_private_key[:6] + "..." + settings.base_private_key[-4:]
        print(f"   ✅ 私钥已配置: {masked} (长度: {len(settings.base_private_key)})")
        
        # 检查格式
        if not settings.base_private_key.startswith("0x"):
            print(f"   ⚠️  警告: 私钥应该以0x开头")
            issues.append("私钥格式建议: 0x开头的64位十六进制")
    else:
        print(f"   ❌ 私钥未配置")
        issues.append("需要在.env中设置: BASE_PRIVATE_KEY=0x...")
    
    # 4. 检查PING代币配置
    print(f"\n4️⃣  PING代币配置")
    try:
        ping_config = get_token_config("PING")
        print(f"   代币名称: {ping_config['name']}")
        print(f"   合约地址: {ping_config['address']}")
        print(f"   精度: {ping_config['decimals']}")
        print(f"   链: {ping_config['chain']}")
        print(f"   DEX: {ping_config['dex']}")
        
        if ping_config['address'] == "0xd85c31854c2b0fb40aaa9e2fc4da23c21f829d46":
            print(f"   ✅ PING地址已正确配置")
        else:
            print(f"   ⚠️  PING地址可能不正确")
    except Exception as e:
        print(f"   ❌ PING配置错误: {e}")
        issues.append("PING代币配置有误")
    
    # 5. 检查Uniswap合约配置
    print(f"\n5️⃣  Uniswap合约配置")
    uniswap = BASE_CONFIG["uniswap_v4"]
    print(f"   Router: {uniswap['swap_router']}")
    print(f"   Factory: {uniswap['pool_manager']}")
    print(f"   Quoter: {uniswap['quoter']}")
    print(f"   ✅ Uniswap合约已配置")
    
    # 6. 检查DEX交易参数
    print(f"\n6️⃣  DEX交易参数")
    print(f"   最大滑点: {settings.dex_max_slippage * 100}%")
    print(f"   交易截止时间: {settings.dex_deadline_seconds}秒")
    print(f"   ✅ 交易参数已配置")
    
    # 总结
    print("\n" + "="*60)
    print("📊 配置检查结果")
    print("="*60)
    
    if issues:
        print(f"\n⚠️  发现 {len(issues)} 个问题:\n")
        for i, issue in enumerate(issues, 1):
            print(f"   {i}. {issue}")
        print(f"\n请修复上述问题后再运行测试。")
        return False
    else:
        print(f"\n✅ 所有配置检查通过！")
        print(f"\n下一步: 运行 python test_dex_ping.py 进行功能测试")
        return True


if __name__ == "__main__":
    check_dex_config()

