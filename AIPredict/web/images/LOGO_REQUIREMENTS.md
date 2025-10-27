# Logo文件需求清单

## 📁 目录结构
```
web/images/
├── coins/           # 代币Logo
├── news_sources/    # 消息来源Logo
├── aster.jpg        # ✅ 已存在
├── hyperliquid.png  # ✅ 已存在
├── gpt4.png         # ✅ 已存在
├── gemini.png       # ✅ 已存在
├── grok.jpg         # ✅ 已存在
├── deepseek.jpg     # ✅ 已存在
├── claude.jpg       # ✅ 已存在
└── qwen.jpg         # ✅ 已存在
```

## 📥 需要添加的Logo文件

### 1. 代币Logo (coins/)
保存到: `web/images/coins/`

| 文件名 | 币种 | 建议来源 |
|--------|------|---------|
| `btc.png` | Bitcoin | https://cryptologos.cc/logos/bitcoin-btc-logo.png |
| `eth.png` | Ethereum | https://cryptologos.cc/logos/ethereum-eth-logo.png |
| `sol.png` | Solana | https://cryptologos.cc/logos/solana-sol-logo.png |
| `mon.png` | Monad | https://assets.coingecko.com/coins/images/34849/standard/mon.png |
| `mega.png` | MegaETH | https://s2.coinmarketcap.com/static/img/coins/64x64/33626.png |
| `ping.png` | PING | https://dd.dexscreener.com/ds-data/tokens/base/0xd85c31854c2b0fb40aaa9e2fc4da23c21f829d46.png |
| `payai.png` | PayAI | https://s2.coinmarketcap.com/static/img/coins/64x64/31984.png |

### 2. 交易平台Logo
保存到: `web/images/`

| 文件名 | 平台 | 建议来源 |
|--------|------|---------|
| `uniswap.png` | Uniswap V4 | https://cryptologos.cc/logos/uniswap-uni-logo.png |
| `pancakeswap.png` | PancakeSwap | https://cryptologos.cc/logos/pancakeswap-cake-logo.png |

### 3. 消息来源Logo (news_sources/)
保存到: `web/images/news_sources/`

| 文件名 | 来源 | 建议来源 |
|--------|------|---------|
| `binance.png` | Binance | https://cryptologos.cc/logos/binance-coin-bnb-logo.png |
| `upbit.png` | Upbit | https://static.upbit.com/logos/upbit.png 或搜索Upbit logo |
| `user.png` | 用户提交 | 任意用户图标即可 |

## 📏 建议尺寸
- 代币Logo: 64x64px 或 128x128px (正方形)
- 平台Logo: 64x64px 或 128x128px (正方形)
- AI模型Logo: 已存在，无需修改
- 消息来源Logo: 64x64px 或 128x128px (正方形)

## 🎨 格式要求
- 格式: PNG (支持透明背景) 或 JPG
- 背景: 最好是透明背景或纯色背景
- 质量: 清晰，避免模糊

## ⚡ 快速下载方法

### 方法1: 使用curl下载
```bash
# 进入目录
cd /Users/cyimon/Work/Dev/AIMarket/AIPredict/web/images

# 下载代币Logo
curl -o coins/btc.png "https://cryptologos.cc/logos/bitcoin-btc-logo.png"
curl -o coins/eth.png "https://cryptologos.cc/logos/ethereum-eth-logo.png"
curl -o coins/sol.png "https://cryptologos.cc/logos/solana-sol-logo.png"
# ... 其他币种

# 下载平台Logo
curl -o uniswap.png "https://cryptologos.cc/logos/uniswap-uni-logo.png"
curl -o pancakeswap.png "https://cryptologos.cc/logos/pancakeswap-cake-logo.png"

# 下载消息来源Logo
curl -o news_sources/binance.png "https://cryptologos.cc/logos/binance-coin-bnb-logo.png"
```

### 方法2: 手动下载
1. 访问建议来源URL
2. 右键保存图片
3. 重命名为对应文件名
4. 保存到对应目录

## ✅ 检查清单
- [ ] coins/btc.png
- [ ] coins/eth.png
- [ ] coins/sol.png
- [ ] coins/mon.png
- [ ] coins/mega.png
- [ ] coins/ping.png
- [ ] coins/payai.png
- [ ] uniswap.png
- [ ] pancakeswap.png
- [ ] news_sources/binance.png
- [ ] news_sources/upbit.png
- [ ] news_sources/user.png

## 📝 注意事项
1. Logo文件名必须全部小写
2. 确保文件扩展名正确 (.png 或 .jpg)
3. 如果logo加载失败，前端会自动隐藏图标
4. 可以先不下载所有logo，系统会优雅降级显示文字

