# DEX交易设置指南

## 🎯 目标

集成Base链（Uniswap V4）和BSC链（PancakeSwap），支持更多代币交易。

---

## ✅ 已完成

### **1. 基础架构** ✅
- [x] DEX客户端基类 (`trading/dex/base_dex_client.py`)
- [x] DEX配置文件 (`trading/dex/dex_config.py`)
- [x] Uniswap V4客户端 (`trading/dex/uniswap_v4_client.py`)
- [x] 模块导出 (`trading/dex/__init__.py`)

### **2. 配置文件** ✅
- [x] Settings添加DEX配置 (`config/settings.py`)
- [x] env.example添加示例配置 (`env.example.txt`)

### **3. 文档** ✅
- [x] 实施计划 (`DEX_INTEGRATION_PLAN.md`)
- [x] 设置指南 (本文件)

---

## ⏳ 待完成

### **1. 依赖安装**
```bash
pip install uniswap-python>=0.7.0
```

### **2. 配置PING代币地址**

需要更新 `trading/dex/dex_config.py` 中的PING代币地址：

```python
BASE_TOKENS: Dict[str, Dict] = {
    "PING": {
        "name": "Ping",
        "address": "0x...",  # ⏳ 需要填写实际地址
        "decimals": 18,
        "chain": "base",
        "dex": "uniswap_v4",
        "base_pair": "USDC",
    },
    # ...
}
```

**获取PING代币地址方法**：
1. 访问 Base链浏览器：https://basescan.org
2. 搜索 "PING token"
3. 复制代币合约地址

### **3. 配置Uniswap V4合约地址**

更新 `trading/dex/dex_config.py` 中的合约地址：

```python
BASE_CONFIG = {
    # ...
    "uniswap_v4": {
        "pool_manager": "0x...",  # ⏳ 需要更新
        "swap_router": "0x2626664c2603336E57B271c5C0b26F421741e481",  # SwapRouter02
        "quoter": "0x...",  # ⏳ 需要更新
    }
}
```

**获取Uniswap V4合约地址**：
1. 访问 Uniswap文档：https://docs.uniswap.org/contracts/v4/deployments
2. 查找Base链上的合约地址
3. 更新配置文件

### **4. 准备Base链账户**

```bash
# 生成新的私钥（或使用现有）
# 可以使用MetaMask或其他钱包生成

# 确保账户有：
# 1. ETH（用于Gas费，建议>0.01 ETH）
# 2. USDC（用于交易，建议>100 USDC）
```

### **5. 配置环境变量**

在 `.env` 文件中添加：

```bash
# Base链配置
BASE_CHAIN_ENABLED=True
BASE_RPC_URL=https://mainnet.base.org
BASE_PRIVATE_KEY=0xYOUR_PRIVATE_KEY_HERE

# DEX交易参数
DEX_MAX_SLIPPAGE=0.01
DEX_DEADLINE_SECONDS=300
```

### **6. 集成到消息交易系统**

需要修改 `news_trading/news_handler.py`：

```python
from trading.dex import is_dex_token, get_token_chain, UniswapV4Client

def get_trading_client(coin: str):
    """根据代币选择交易客户端"""
    if is_dex_token(coin):
        chain = get_token_chain(coin)
        if chain == "base":
            return UniswapV4Client(
                private_key=settings.base_private_key,
                rpc_url=settings.base_rpc_url
            )
        elif chain == "bsc":
            # TODO: 实现PancakeSwap客户端
            pass
    else:
        # CEX代币，使用Hyperliquid
        return HyperliquidClient(...)
```

### **7. 测试流程**

```python
# 创建测试脚本 test_dex.py
import asyncio
from trading.dex import UniswapV4Client
from config.settings import settings

async def test_uniswap():
    # 初始化客户端
    client = UniswapV4Client(
        private_key=settings.base_private_key,
        rpc_url=settings.base_rpc_url
    )
    
    # 1. 测试账户信息
    account_info = await client.get_account_info()
    print(f"账户信息: {account_info}")
    
    # 2. 测试代币余额
    usdc_address = "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913"
    usdc_balance = await client.get_token_balance(usdc_address)
    print(f"USDC余额: {usdc_balance}")
    
    # 3. 测试小额swap（建议先用1-10 USDC测试）
    # result = await client.place_order(
    #     coin="PING",
    #     is_buy=True,
    #     sz=10,  # 10 USDC
    # )
    # print(f"交易结果: {result}")

if __name__ == "__main__":
    asyncio.run(test_uniswap())
```

---

## 🔒 安全提示

1. **私钥管理**
   - ⚠️ 永远不要提交私钥到Git
   - ⚠️ 使用独立账户进行测试
   - ⚠️ 生产环境使用硬件钱包或KMS

2. **资金安全**
   - 测试阶段使用小额资金（<$100）
   - 确认合约地址正确
   - 检查滑点设置合理

3. **Gas费**
   - Base链Gas较低但仍需ETH
   - 建议账户至少保留0.01 ETH

---

## 📊 代币支持

### **当前配置的代币**

**Base链（Uniswap V4）**:
- PING ⏳ 待配置地址
- USDC ✅
- WETH ✅

**BSC链（PancakeSwap）**:
- USDT ✅
- WBNB ✅
- BUSD ✅

### **添加新代币**

编辑 `trading/dex/dex_config.py`:

```python
BASE_TOKENS: Dict[str, Dict] = {
    "YOUR_TOKEN": {
        "name": "Your Token Name",
        "address": "0x...",  # 代币合约地址
        "decimals": 18,      # 代币精度
        "chain": "base",
        "dex": "uniswap_v4",
        "base_pair": "USDC",  # 交易对
    },
    # ...
}
```

---

## 🚀 快速开始（MVP测试）

### **最小化测试 - 只测试PING**

1. **准备工作**
```bash
# 1. 安装依赖
pip install uniswap-python

# 2. 获取PING代币地址（TODO）
# 3. 准备Base账户（ETH + USDC）
```

2. **配置 `.env`**
```bash
BASE_CHAIN_ENABLED=True
BASE_PRIVATE_KEY=0xYOUR_KEY
```

3. **更新代币地址**
```python
# trading/dex/dex_config.py
"PING": {
    "address": "0xREAL_PING_ADDRESS",  # 填写实际地址
    # ...
}
```

4. **运行测试**
```bash
python test_dex.py
```

---

## ❓ 常见问题

### **Q: 如何获取Base链测试币？**
A: Base链使用真实ETH，可以从以太坊主网桥接到Base。测试建议使用小额（<0.01 ETH）。

### **Q: Uniswap V4和V3有什么区别？**
A: V4引入了Hooks机制，但基本swap接口类似。当前实现基于SwapRouter02，兼容V3/V4。

### **Q: 如何确认交易成功？**
A: 
1. 检查返回的`tx_hash`
2. 在 https://basescan.org 查询交易
3. 检查代币余额变化

### **Q: 交易失败怎么办？**
A: 常见原因：
1. Gas不足（增加ETH余额）
2. 滑点过大（增加slippage）
3. 流动性不足（减小交易金额）
4. 代币未授权（自动处理，但可能需要单独交易）

---

## 📞 后续步骤

完成MVP后：

1. ✅ **验证PING交易**
   - 小额买入测试
   - 检查余额变化
   - 确认Gas消耗

2. ⏳ **实现PancakeSwap客户端**
   - 类似Uniswap实现
   - 支持BSC链代币

3. ⏳ **集成到消息交易**
   - 自动路由到对应DEX
   - 统一交易接口

4. ⏳ **添加价格查询**
   - 从池子获取实时价格
   - 滑点计算优化

5. ⏳ **增强错误处理**
   - Gas估算
   - 交易重试
   - 流动性检查

---

**准备好后，按照TODO列表逐步完成配置！** 🚀

