# AsterDex 接入配置指南

## 概述

本系统已成功接入 AsterDex Futures API V3，可以在 AsterDex 平台上进行自动化交易。

**API 文档参考**: [AsterDex API Docs](https://github.com/asterdex/api-docs)

## 前提条件

### 1. 创建 AsterDex 账户

1. 访问 https://www.asterdex.com
2. 注册并完成 KYC（如需要）
3. 充值 USDT 到合约账户

### 2. 创建 API Wallet (AGENT)

⚠️ **重要**: AsterDex 使用独特的 API Wallet 机制

1. 访问 https://www.asterdex.com/en/api-wallet
2. 切换到顶部的 `Pro API` 标签
3. 创建新的 API Wallet (AGENT)
4. 保存以下信息：
   - **User Address**: 你的主钱包地址 (EOA)
   - **Signer Address**: API Wallet 地址
   - **Private Key**: API Wallet 私钥

### 3. API Wallet 授权

创建 API Wallet 后，它会自动被授权进行交易操作。

## 配置步骤

### 1. 安装依赖

```bash
cd AIPredict
pip install -r requirements.txt
```

主要依赖：
- `eth-account==0.13.7` - 以太坊账户管理
- `eth-abi==5.2.0` - ABI 编码
- `web3==7.11.0` - Web3 支持

### 2. 配置环境变量

编辑 `.env` 文件（如果没有，复制 `env.example.txt`）：

```bash
# 启用 Aster 平台
ENABLED_PLATFORMS=aster
# 或同时启用 Hyperliquid 和 Aster 进行对比
# ENABLED_PLATFORMS=hyperliquid,aster

# Aster 配置
ASTER_TESTNET=False  # Aster 没有测试网，直接使用主网
ASTER_API_URL=https://fapi.asterdex.com

# Alpha 组配置（使用 API Wallet 的私钥）
GROUP_1_NAME=Alpha组
GROUP_1_PRIVATE_KEY=0x4fd0a42218f3eae43a6ce26d22544e986139a01e5b34a62db53757ffca81bae1  # 替换为你的 API Wallet 私钥
GROUP_1_TESTNET=False

# Beta 组配置
GROUP_2_NAME=Beta组
GROUP_2_PRIVATE_KEY=0x...  # 另一个 API Wallet 私钥
GROUP_2_TESTNET=False

# AI API Keys
CLAUDE_API_KEY=sk-ant-...
OPENAI_API_KEY=sk-...
# ... 其他配置
```

### 3. 验证配置

运行测试脚本验证连接：

```python
import asyncio
from trading.aster.client import AsterClient

async def test():
    client = AsterClient(
        private_key="0x你的API_Wallet私钥",
        testnet=False
    )
    
    # 测试获取账户信息
    account = await client.get_account_info()
    print(f"账户余额: ${account['marginSummary']['accountValue']}")
    
    # 测试获取市场数据
    market = await client.get_market_data("BTC")
    print(f"BTC价格: ${market['price']}")
    
    await client.close_session()

asyncio.run(test())
```

## API 端点说明

### 基础信息

- **Base URL**: `https://fapi.asterdex.com`
- **API 版本**: V3 (订单相关) / V1 (市场数据)
- **签名方式**: EIP-191 标准 (eth_account)

### 主要端点

#### 市场数据（无需签名）

| 端点 | 说明 |
|------|------|
| `GET /fapi/v1/ticker/24hr` | 24小时行情 |
| `GET /fapi/v1/depth` | 订单簿 |
| `GET /fapi/v1/trades` | 最近成交 |
| `GET /fapi/v1/klines` | K线数据 |
| `GET /fapi/v1/exchangeInfo` | 交易所信息 |

#### 交易操作（需要签名）

| 端点 | 说明 |
|------|------|
| `POST /fapi/v3/order` | 下单 |
| `GET /fapi/v3/order` | 查询订单 |
| `DELETE /fapi/v1/order` | 取消订单 |
| `GET /fapi/v1/openOrders` | 未成交订单 |
| `GET /fapi/v3/account` | 账户信息 |
| `GET /fapi/v3/balance` | 余额信息 |
| `GET /fapi/v3/positionRisk` | 持仓信息 |
| `GET /fapi/v1/userTrades` | 历史成交 |

### 币种格式

AsterDex 使用标准的币对格式：
- BTC → **BTCUSDT**
- ETH → **ETHUSDT**

系统会自动转换。

## 签名机制

AsterDex 使用独特的签名方式：

```python
# 1. 生成 nonce (微秒级时间戳)
nonce = math.trunc(time.time() * 1000000)

# 2. 准备参数
params = {
    "symbol": "BTCUSDT",
    "side": "BUY",
    "type": "LIMIT",
    "quantity": "0.001",
    "price": 50000,
    "recvWindow": 50000,
    "timestamp": int(time.time() * 1000)
}

# 3. 转换所有值为字符串
params_str = {k: str(v) for k, v in params.items()}

# 4. JSON 序列化 (排序 key)
json_str = json.dumps(params_str, sort_keys=True)

# 5. ABI 编码
encoded = eth_abi.encode(
    ['string', 'address', 'address', 'uint256'],
    [json_str, user_address, signer_address, nonce]
)

# 6. Keccak256 哈希
message_hash = Web3.keccak(encoded).hex()

# 7. EIP-191 签名
signable_msg = encode_defunct(hexstr=message_hash)
signed = Account.sign_message(signable_msg, private_key)

# 8. 添加签名参数
params['nonce'] = nonce
params['user'] = user_address
params['signer'] = signer_address
params['signature'] = '0x' + signed.signature.hex()
```

系统已自动实现，无需手动处理。

## 下单示例

### 限价买入

```python
result = await client.place_order(
    coin="BTC",
    is_buy=True,
    size=0.001,
    price=50000,
    order_type="Limit",
    reduce_only=False
)
```

### 市价卖出

```python
result = await client.place_order(
    coin="BTC",
    is_buy=False,
    size=0.001,
    price=None,  # None 表示市价
    order_type="Market",
    reduce_only=False
)
```

### 平仓

```python
result = await client.place_order(
    coin="BTC",
    is_buy=False,  # 平多仓
    size=0.001,
    price=50000,
    order_type="Limit",
    reduce_only=True  # 只减仓
)
```

## 运行多平台交易

### 单 Aster 平台

```bash
# 配置
ENABLED_PLATFORMS=aster

# 运行
python consensus_arena_multiplatform.py
```

### Hyperliquid + Aster 对比

```bash
# 配置
ENABLED_PLATFORMS=hyperliquid,aster

# 运行
python consensus_arena_multiplatform.py
```

## 注意事项

### 1. API Wallet vs 主钱包

- **User Address**: 你的主钱包地址（持有资金）
- **Signer Address**: API Wallet 地址（用于签名）
- **Private Key**: API Wallet 的私钥（不是主钱包私钥）

⚠️ **安全**: API Wallet 有权限进行交易，但无法提现。

### 2. 费率

查看当前费率：
```python
account = await client.get_account_info()
# 在返回的数据中查找 fee rate
```

### 3. 精度要求

- **数量精度**: 最小 0.00001
- **价格精度**: 最小 0.01
- 系统会自动处理精度

### 4. 订单类型

支持的订单类型：
- `LIMIT` - 限价单
- `MARKET` - 市价单
- `STOP` - 止损单
- `TAKE_PROFIT` - 止盈单

### 5. 持仓模式

默认使用 `positionSide: "BOTH"` (单向持仓)

如需双向持仓，请修改：
```python
# 在 place_order 中
"positionSide": "LONG"  # 或 "SHORT"
```

### 6. 时间同步

确保系统时间准确，否则签名会失败：
```bash
# macOS
sudo sntp -sS time.apple.com

# Linux
sudo ntpdate ntp.ubuntu.com
```

### 7. 请求限制

- 请求频率: 1200 次/分钟
- 订单频率: 300 单/分钟
- 超限会返回 429 错误

## 常见问题

### Q: 签名验证失败？

A: 检查：
1. API Wallet 是否正确创建
2. Private Key 是否正确（API Wallet 的，不是主钱包的）
3. User 和 Signer 地址是否正确
4. 系统时间是否同步

### Q: 下单失败 "Insufficient balance"？

A: 确保：
1. 资金在合约账户（不是现货账户）
2. 账户有足够的 USDT
3. 考虑保证金和手续费

### Q: 无法获取账户信息？

A: 确认：
1. API Wallet 已创建并授权
2. 网络连接正常
3. API 端点正确

### Q: 如何查看交易日志？

A: 系统会自动打印详细日志，包括：
- 订单提交
- 订单状态
- 成交信息
- 错误详情

## 监控和调试

### 查看实时日志

```bash
python consensus_arena_multiplatform.py 2>&1 | tee aster_trading.log
```

### 查看API调用

在客户端中已包含详细日志：
```python
logger.info(f"[Aster] 📊 下单: {symbol} {side} {size} @ ${price}")
```

### 平台对比数据

访问 API 查看对比：
```bash
curl http://localhost:46000/api/platform_comparison
```

## 技术支持

- **AsterDex 官网**: https://www.asterdex.com
- **API 文档**: https://github.com/asterdex/api-docs
- **Discord**: https://discord.gg/asterdex (查看最新链接)

## 总结

✅ 已完成 AsterDex 集成
✅ 支持完整的交易功能
✅ 与 Hyperliquid 统一接口
✅ 支持多平台对比交易

现在可以开始在 AsterDex 上进行 AI 自动化交易了！

