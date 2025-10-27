# DEX集成计划 - Base & BSC链支持

## 🎯 **目标**

支持多链DEX交易，扩展系统支持更多代币：
1. **Base链**：Uniswap V4 - 支持PING等代币
2. **BSC链**：PancakeSwap - 支持BSC生态代币

---

## 🏗️ **架构设计**

### **当前架构**
```
CEX永续合约
├── Hyperliquid
└── Aster
```

### **新架构**
```
交易后端（多个）
├── CEX（中心化交易所）
│   ├── Hyperliquid（永续合约）✅ 已有
│   └── Aster（永续合约）✅ 已有
│
└── DEX（去中心化交易所）
    ├── Uniswap V4 (Base链) ⭐ 新增
    └── PancakeSwap (BSC链) ⭐ 新增
```

---

## 📊 **CEX vs DEX 差异**

| 特性 | CEX（Hyperliquid/Aster） | DEX（Uniswap/PancakeSwap） |
|------|-------------------------|---------------------------|
| **交易类型** | 永续合约（Perpetual Futures） | 现货交换（Spot Swap） |
| **杠杆** | 支持（10-50x） | 不支持（1x） |
| **保证金** | 需要保证金 | 全额代币交换 |
| **止盈止损** | 支持 | 需要自己实现 |
| **滑点** | 低 | 可能较高 |
| **Gas费** | 无 | 有（链上交易） |
| **做空** | 支持 | 需要借贷协议 |

---

## 🔧 **技术栈选择**

### **Base链（Uniswap V4）**

#### **必需工具**
1. **Web3.py** - Python以太坊交互库
2. **Uniswap V4 SDK** - Uniswap V4合约交互
3. **Base RPC** - Base链节点

#### **关键合约**
```python
# Base链配置
CHAIN_ID = 8453  # Base主网
RPC_URL = "https://mainnet.base.org"

# Uniswap V4合约地址
UNISWAP_V4_POOL_MANAGER = "0x..."  # Pool Manager
UNISWAP_V4_SWAP_ROUTER = "0x..."   # Swap Router

# PING代币
PING_TOKEN_ADDRESS = "0x..."
USDC_BASE = "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913"  # Base上的USDC
```

#### **交易流程**
```
1. 检查USDC余额
2. 授权Uniswap路由器使用USDC
3. 通过Swap Router交换 USDC → PING
4. 监控交易状态
```

---

### **BSC链（PancakeSwap）**

#### **必需工具**
1. **Web3.py** - Python以太坊交互库
2. **PancakeSwap SDK** - PancakeSwap合约交互
3. **BSC RPC** - BSC节点

#### **关键合约**
```python
# BSC链配置
CHAIN_ID = 56  # BSC主网
RPC_URL = "https://bsc-dataseed.binance.org/"

# PancakeSwap合约地址
PANCAKE_ROUTER_V3 = "0x1b81D678ffb9C0263b24A97847620C99d213eB14"
PANCAKE_FACTORY = "0x..."

# 常用代币
USDT_BSC = "0x55d398326f99059fF775485246999027B3197955"
WBNB = "0xbb4CdB9CBd36B01bD1cBaEBF2De08d9173bc095c"
```

#### **交易流程**
```
1. 检查USDT/BNB余额
2. 授权PancakeSwap路由器
3. 通过Router交换代币
4. 监控交易状态
```

---

## 📝 **实现步骤**

### **阶段1：基础设施（Week 1）**

#### **1.1 创建DEX客户端基类** ✅ 已创建
```
trading/dex/
├── base_dex_client.py  ✅ 基类
├── uniswap_v4_client.py  ⏳ 待实现
└── pancakeswap_client.py  ⏳ 待实现
```

#### **1.2 环境配置**
```bash
# .env 新增配置
# Base链配置
BASE_CHAIN_ENABLED=True
BASE_RPC_URL=https://mainnet.base.org
BASE_PRIVATE_KEY=0xYOUR_KEY

# BSC链配置
BSC_CHAIN_ENABLED=True
BSC_RPC_URL=https://bsc-dataseed.binance.org/
BSC_PRIVATE_KEY=0xYOUR_KEY

# DEX交易配置
DEX_MAX_SLIPPAGE=0.01  # 1%最大滑点
DEX_DEADLINE=300  # 5分钟交易截止
```

#### **1.3 安装依赖**
```bash
pip install web3==6.11.0
pip install uniswap-python  # Uniswap SDK
pip install pancakeswap-python  # PancakeSwap SDK (如果有)
```

---

### **阶段2：Uniswap V4集成（Week 2）**

#### **2.1 实现Uniswap V4客户端**

**核心功能**：
- ✅ 连接Base链
- ✅ 获取代币余额
- ✅ 获取池子价格
- ✅ 执行Swap交易
- ✅ Gas估算和优化

**示例代码**：
```python
# trading/dex/uniswap_v4_client.py
from web3 import Web3
from .base_dex_client import BaseDEXClient

class UniswapV4Client(BaseDEXClient):
    def __init__(self, private_key: str, rpc_url: str):
        super().__init__("base", private_key, rpc_url)
        self.w3 = Web3(Web3.HTTPProvider(rpc_url))
        # 初始化合约
        
    async def swap_tokens(self, ...):
        # 实现Uniswap V4 swap逻辑
        pass
```

#### **2.2 代币配置**
```python
# 支持的Base链代币
BASE_TOKENS = {
    "PING": {
        "address": "0x...",
        "decimals": 18,
        "pool": "0x..."  # PING/USDC池子
    },
    "USDC": {
        "address": "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913",
        "decimals": 6
    }
}
```

---

### **阶段3：PancakeSwap集成（Week 3）**

#### **3.1 实现PancakeSwap客户端**

**核心功能**：
- ✅ 连接BSC链
- ✅ 获取代币余额
- ✅ 获取价格（通过Router）
- ✅ 执行Swap交易
- ✅ Gas优化（BSC gas较低）

**示例代码**：
```python
# trading/dex/pancakeswap_client.py
from web3 import Web3
from .base_dex_client import BaseDEXClient

class PancakeSwapClient(BaseDEXClient):
    def __init__(self, private_key: str, rpc_url: str):
        super().__init__("bsc", private_key, rpc_url)
        self.w3 = Web3(Web3.HTTPProvider(rpc_url))
        # 初始化合约
        
    async def swap_tokens(self, ...):
        # 实现PancakeSwap swap逻辑
        pass
```

---

### **阶段4：系统集成（Week 4）**

#### **4.1 更新消息交易逻辑**

**修改点**：
1. 根据代币判断使用哪个交易后端
2. CEX代币 → Hyperliquid
3. Base代币 → Uniswap V4
4. BSC代币 → PancakeSwap

```python
# news_trading/news_handler.py
def get_trading_client(coin: str):
    if coin in BASE_TOKENS:
        return UniswapV4Client(...)
    elif coin in BSC_TOKENS:
        return PancakeSwapClient(...)
    else:
        return HyperliquidClient(...)  # 默认CEX
```

#### **4.2 DEX交易策略调整**

**关键差异**：
- ❌ 无杠杆（DEX现货）
- ❌ 无做空（需要借贷）
- ✅ 全额购买代币
- ✅ 设置滑点保护

**策略示例**：
```python
# DEX交易配置
if using_dex:
    leverage = 1  # 无杠杆
    direction = "long"  # 只能做多
    margin_pct = 0.30  # 使用30%余额买入
    slippage = 0.01  # 1%滑点
```

---

## ⚠️ **风险和挑战**

### **技术风险**

1. **Gas费波动**
   - Base链：相对便宜
   - BSC链：非常便宜
   - 解决：Gas价格监控和优化

2. **滑点风险**
   - DEX流动性可能不足
   - 解决：设置合理滑点限制

3. **交易失败**
   - 链上交易可能revert
   - 解决：充分的Gas估算和错误处理

4. **私钥管理**
   - 需要管理多个链的私钥
   - 解决：统一私钥管理，环境变量分离

### **业务风险**

1. **无杠杆限制**
   - DEX只能1x，收益降低
   - 解决：增加仓位比例

2. **无法做空**
   - 上币后价格下跌无法对冲
   - 解决：只在看涨时参与DEX交易

3. **流动性风险**
   - 小币种流动性差
   - 解决：检查池子深度，设置最小流动性要求

---

## 💡 **优化建议**

### **短期（立即实施）**

1. **混合策略**
   - CEX代币：使用Hyperliquid（杠杆交易）
   - DEX代币：使用Uniswap/PancakeSwap（现货）

2. **风险控制**
   - DEX交易使用更小的仓位（10-20%）
   - 更严格的止损（5-10%）

3. **Gas优化**
   - 预估Gas并在低费时交易
   - 使用EIP-1559优化

### **长期（逐步实施）**

1. **流动性聚合**
   - 对比多个DEX价格
   - 选择最优路由

2. **借贷集成**
   - 集成Aave等借贷协议
   - 实现DEX上的杠杆和做空

3. **跨链桥**
   - 自动跨链调度资金
   - 优化资金利用效率

---

## 📋 **检查清单**

### **实施前**
- [ ] 确认Base和BSC RPC节点可用
- [ ] 准备测试私钥和测试币
- [ ] 安装必要的Python库
- [ ] 测试Web3连接

### **实施中**
- [ ] 实现Uniswap V4客户端
- [ ] 实现PancakeSwap客户端
- [ ] 集成到消息交易系统
- [ ] 添加代币配置

### **实施后**
- [ ] 小额测试交易
- [ ] 监控Gas消耗
- [ ] 验证滑点控制
- [ ] 测试错误处理

---

## 🚀 **快速开始（MVP）**

### **最小可行产品 - 仅支持PING**

**步骤**：
1. ✅ 创建基础架构（已完成）
2. ⏳ 实现基础Uniswap V4客户端（仅PING）
3. ⏳ 配置PING代币信息
4. ⏳ 修改消息交易逻辑支持Base链
5. ⏳ 测试PING交易流程

**预计时间**：3-5天

---

## 📞 **需要决策的问题**

1. **私钥管理**
   - Q: Base和BSC使用同一个私钥还是分开？
   - 建议：分开管理，降低风险

2. **资金分配**
   - Q: 每条链分配多少资金？
   - 建议：Base $100, BSC $100（测试阶段）

3. **优先级**
   - Q: 先实现Base还是BSC？
   - 建议：先Base（PING需求），再BSC

4. **DEX选择**
   - Q: Base上只用Uniswap V4还是支持多个DEX？
   - 建议：初期只Uniswap V4，后续扩展

---

**准备开始实施吗？需要我先实现哪一部分？** 🚀

建议优先级：
1. **Uniswap V4客户端（支持PING）** - 最高优先级
2. PancakeSwap客户端 - 中等优先级
3. 流动性聚合 - 低优先级

