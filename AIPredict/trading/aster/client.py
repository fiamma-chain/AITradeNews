"""
Aster 交易客户端实现
基于 AsterDex Futures API V3
文档: https://github.com/asterdex/api-docs
"""
import logging
import time
import asyncio
import json
import math
from typing import Dict, List, Optional
import aiohttp
from eth_account import Account
from eth_account.messages import encode_defunct
from eth_abi import encode
from web3 import Web3
from decimal import Decimal, ROUND_DOWN, ROUND_HALF_UP

from trading.base_client import BaseExchangeClient
from trading.precision_config import precision_config
from config.settings import settings

logger = logging.getLogger(__name__)


class AsterClient(BaseExchangeClient):
    """Aster 交易客户端 - 基于 AsterDex Futures API V3"""
    
    def __init__(self, private_key: str, testnet: bool = True):
        """
        初始化 Aster 客户端
        
        Args:
            private_key: 以太坊私钥（可以带或不带0x前缀）
            testnet: 是否使用测试网
        
        注意：需要从 https://www.asterdex.com/en/api-wallet 创建 API Wallet (AGENT)
        """
        super().__init__(private_key, testnet)
        
        # 确保私钥格式正确
        if not private_key.startswith('0x'):
            private_key = '0x' + private_key
        
        # API 基础 URL (AsterDex 官方)
        self.base_url = "https://fapi.asterdex.com"
        
        # 从私钥生成账户
        account = Account.from_key(private_key)
        self.address = account.address  # 这是 user 地址
        self.account = account
        self.private_key = private_key
        
        # 注意：AsterDex 需要 signer 和 user 分离
        # signer 是 API Wallet 地址，需要从 https://www.asterdex.com/en/api-wallet 获取
        # 这里默认使用同一个地址，实际使用时需要配置正确的 signer
        self.signer = account.address
        
        # 会话管理
        self.session: Optional[aiohttp.ClientSession] = None
        
        logger.info(f"✅ Aster 客户端初始化成功")
        logger.info(f"   User地址: {self.address}")
        logger.info(f"   Signer地址: {self.signer}")
        logger.info(f"   ⚠️  请确保已在 https://www.asterdex.com/en/api-wallet 创建 API Wallet")
    
    @property
    def platform_name(self) -> str:
        """平台名称"""
        return "Aster"
    
    async def _get_session(self) -> aiohttp.ClientSession:
        """获取或创建 aiohttp 会话"""
        if self.session is None or self.session.closed:
            self.session = aiohttp.ClientSession()
        return self.session
    
    def _trim_dict(self, my_dict: Dict) -> Dict:
        """转换字典值为字符串（AsterDex 要求）"""
        for key in my_dict:
            value = my_dict[key]
            if isinstance(value, list):
                new_value = []
                for item in value:
                    if isinstance(item, dict):
                        new_value.append(json.dumps(self._trim_dict(item)))
                    else:
                        new_value.append(str(item))
                my_dict[key] = json.dumps(new_value)
                continue
            if isinstance(value, dict):
                my_dict[key] = json.dumps(self._trim_dict(value))
                continue
            my_dict[key] = str(value)
        return my_dict
    
    def _trim_param(self, params: Dict, nonce: int) -> str:
        """生成签名消息 hash"""
        self._trim_dict(params)
        json_str = json.dumps(params, sort_keys=True).replace(' ', '').replace('\'', '\"')
        
        # 使用 eth_abi 编码
        encoded = encode(
            ['string', 'address', 'address', 'uint256'],
            [json_str, self.address, self.signer, nonce]
        )
        
        # 计算 keccak256 hash
        keccak_hex = Web3.keccak(encoded).hex()
        return keccak_hex
    
    def _sign_request(self, params: Dict) -> Dict:
        """
        签名请求（AsterDex 签名算法）
        
        Args:
            params: 请求参数
            
        Returns:
            签名后的参数（包含 signature, nonce, user, signer）
        """
        # 生成 nonce (微秒级时间戳)
        nonce = math.trunc(time.time() * 1000000)
        
        # 移除 None 值
        params = {key: value for key, value in params.items() if value is not None}
        
        # 添加必需参数
        params['recvWindow'] = 50000
        params['timestamp'] = int(round(time.time() * 1000))
        
        # 生成签名消息
        msg = self._trim_param(params.copy(), nonce)
        signable_msg = encode_defunct(hexstr=msg)
        signed_message = Account.sign_message(signable_message=signable_msg, private_key=self.private_key)
        
        # 添加签名相关参数
        params['nonce'] = nonce
        params['user'] = self.address
        params['signer'] = self.signer
        params['signature'] = '0x' + signed_message.signature.hex()
        
        return params
    
    async def _request(
        self,
        method: str,
        endpoint: str,
        params: Dict = None,
        signed: bool = False
    ) -> Dict:
        """
        发送 API 请求
        
        Args:
            method: HTTP 方法
            endpoint: API 端点
            params: 请求参数
            signed: 是否需要签名
            
        Returns:
            响应数据
        """
        session = await self._get_session()
        url = f"{self.base_url}{endpoint}"
        
        if params is None:
            params = {}
        
        # 如果需要签名，添加签名参数
        if signed:
            params = self._sign_request(params)
        
        try:
            headers = {
                'Content-Type': 'application/x-www-form-urlencoded',
                'User-Agent': 'AIPredict/1.0'
            }
            
            if method == "GET":
                async with session.get(url, params=params, headers=headers, timeout=aiohttp.ClientTimeout(total=30)) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        logger.error(f"[Aster] API 错误 {response.status}: {error_text}")
                    response.raise_for_status()
                    return await response.json()
            elif method == "POST":
                async with session.post(url, data=params, headers=headers, timeout=aiohttp.ClientTimeout(total=30)) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        logger.error(f"[Aster] API 错误 {response.status}: {error_text}")
                    response.raise_for_status()
                    return await response.json()
            elif method == "DELETE":
                async with session.delete(url, data=params, headers=headers, timeout=aiohttp.ClientTimeout(total=30)) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        logger.error(f"[Aster] API 错误 {response.status}: {error_text}")
                    response.raise_for_status()
                    return await response.json()
            else:
                raise ValueError(f"Unsupported HTTP method: {method}")
        
        except aiohttp.ClientError as e:
            logger.error(f"[Aster] API 请求失败: {e}")
            raise
        except Exception as e:
            logger.error(f"[Aster] 请求异常: {e}")
            raise
    
    async def get_account_info(self) -> Dict:
        """获取账户信息"""
        try:
            # 获取账户信息 (V3)
            result = await self._request("GET", "/fapi/v3/account", signed=True)
            
            # 获取余额（统计 USDC + USDT，使用marginBalance包含未实现盈亏）
            # Aster使用USDT作为合约保证金，需要同时统计USDC和USDT
            total_wallet_balance = 0.0
            total_unrealized_profit = 0.0
            total_margin_balance = 0.0
            total_available_balance = 0.0
            
            if 'assets' in result:
                for asset in result['assets']:
                    asset_type = asset.get('asset', '')
                    if asset_type in ['USDC', 'USDT']:  # 统计USDC和USDT余额
                        wallet_balance = float(asset.get('walletBalance', 0))
                        margin_balance = float(asset.get('marginBalance', 0))  # marginBalance = walletBalance + unrealizedProfit
                        unrealized_profit = float(asset.get('unrealizedProfit', 0))
                        available_balance = float(asset.get('availableBalance', 0))
                        
                        # 使用marginBalance作为实际余额（包含未实现盈亏）
                        total_wallet_balance += wallet_balance
                        total_margin_balance += margin_balance
                        total_unrealized_profit += unrealized_profit
                        total_available_balance += available_balance
                        
                        logger.info(f"[Aster] {asset_type} - 钱包:{wallet_balance:.6f} 保证金:{margin_balance:.6f} 未实现盈亏:{unrealized_profit:.6f}")
            
            # 输出总余额（USDC + USDT）
            logger.info(f"[Aster] 📊 合约账户总余额: ${total_margin_balance:.6f} (USDC+USDT)")
            
            # 标准化返回格式，兼容 Hyperliquid 格式，同时包含 Aster 详细信息
            # 使用marginBalance（包含未实现盈亏）作为账户价值
            return {
                "marginSummary": {
                    "accountValue": total_margin_balance  # 使用marginBalance而不是walletBalance
                },
                "assetPositions": result.get('positions', []),
                "withdrawable": total_available_balance,  # 兼容 Hyperliquid 格式
                # Aster 特有字段
                "equity": total_margin_balance,
                "availableBalance": total_available_balance,
                "totalPositionInitialMargin": float(result.get('totalPositionInitialMargin', 0)),
                "totalUnrealizedProfit": total_unrealized_profit,
                "positions": result.get('positions', []),
                "raw": result
            }
        except Exception as e:
            logger.error(f"[Aster] 获取账户信息失败: {e}")
            return {"marginSummary": {"accountValue": 0}, "assetPositions": []}
    
    async def get_market_data(self, coin: str) -> Dict:
        """获取市场数据"""
        try:
            # 转换币种格式 (BTC -> BTCUSDT)
            symbol = f"{coin}USDT" if not coin.endswith('USDT') else coin
            
            # 获取 24小时行情
            result = await self._request("GET", "/fapi/v1/ticker/24hr", params={"symbol": symbol})
            
            return {
                "coin": coin,
                "price": float(result.get('lastPrice', 0)),
                "mark_price": float(result.get('lastPrice', 0)),  # Aster 没有单独的 mark price 接口
                "funding_rate": 0.0,  # 需要单独获取
                "open_interest": float(result.get('openInterest', 0)),
                "change_24h": float(result.get('priceChangePercent', 0)),
                "volume": float(result.get('volume', 0)),
                "raw_ctx": result
            }
        except Exception as e:
            logger.error(f"[Aster] 获取市场数据失败: {e}")
            raise
    
    async def get_orderbook(self, coin: str) -> Dict:
        """获取订单簿"""
        try:
            symbol = f"{coin}USDT" if not coin.endswith('USDT') else coin
            result = await self._request("GET", "/fapi/v1/depth", params={"symbol": symbol, "limit": 20})
            
            bids = [[float(b[0]), float(b[1])] for b in result.get('bids', [])]
            asks = [[float(a[0]), float(a[1])] for a in result.get('asks', [])]
            
            return {"bids": bids, "asks": asks}
        except Exception as e:
            logger.error(f"[Aster] 获取订单簿失败: {e}")
            return {"bids": [], "asks": []}
    
    async def get_recent_trades(self, coin: str, limit: int = 20) -> List[Dict]:
        """获取最近成交记录"""
        try:
            symbol = f"{coin}USDT" if not coin.endswith('USDT') else coin
            result = await self._request("GET", "/fapi/v1/trades", params={"symbol": symbol, "limit": limit})
            
            return result if isinstance(result, list) else []
        except Exception as e:
            logger.warning(f"[Aster] 获取最近成交失败: {e}")
            return []
    
    def update_leverage(self, coin: str, leverage: int) -> Dict:
        """
        更新杠杆倍数 (同步方法)
        Args:
            coin: 币种
            leverage: 杠杆倍数 (1-125)
        Returns:
            更新结果
        """
        import asyncio
        try:
            # 创建新的event loop来运行异步方法
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            result = loop.run_until_complete(self.update_leverage_async(coin, leverage))
            loop.close()
            return result
        except Exception as e:
            logger.error(f"❌ [Aster] 更新杠杆失败: {e}")
            raise

    async def update_leverage_async(self, coin: str, leverage: int) -> Dict:
        """
        更新杠杆倍数 (异步方法)
        Args:
            coin: 币种
            leverage: 杠杆倍数 (1-125)
        Returns:
            更新结果
        """
        try:
            symbol = f"{coin}USDT" if not coin.endswith('USDT') else coin
            
            params = {
                "symbol": symbol,
                "leverage": leverage
            }
            
            # 使用 v3 端点（v1端点在Aster上会返回401）
            result = await self._request("POST", "/fapi/v3/leverage", params=params, signed=True)
            logger.info(f"✅ [Aster] 杠杆已更新: {coin} -> {leverage}x (返回: {result})")
            return result
        except Exception as e:
            logger.error(f"❌ [Aster] 更新杠杆失败: {e}")
            raise

    async def place_order(
        self,
        coin: str,
        is_buy: bool,
        size: float,
        price: float,
        order_type: str = "Limit",
        reduce_only: bool = False,
        leverage: int = None
    ) -> Dict:
        """
        下单（支持杠杆设置）
        Args:
            coin: 币种
            is_buy: 是否买入
            size: 数量
            price: 价格
            order_type: 订单类型
            reduce_only: 是否只减仓
            leverage: 杠杆倍数（可选，如果提供则在下单前设置杠杆）
        """
        try:
            # Aster 平台风控：杠杆限制和保证金要求
            if not reduce_only:
                # 1. 杠杆限制：使用配置的最大杠杆
                max_leverage = int(settings.ai_max_leverage)
                if leverage is not None and leverage > max_leverage:
                    error_msg = f"❌ [Aster] 杠杆不能超过{max_leverage}倍 (当前: {leverage}x, 配置: AI_MAX_LEVERAGE={settings.ai_max_leverage})"
                    logger.error(error_msg)
                    return {"status": "err", "response": error_msg}
                
                # 2. 获取实际价格（用于保证金计算）
                actual_price = price
                if actual_price is None:
                    # 如果没有指定价格，获取当前市价
                    orderbook = await self.get_orderbook(coin)
                    bids = orderbook.get("bids", [])
                    asks = orderbook.get("asks", [])
                    
                    if is_buy:
                        actual_price = float(asks[0][0]) if asks else None
                    else:
                        actual_price = float(bids[0][0]) if bids else None
                    
                    if actual_price is None:
                        error_msg = f"❌ [Aster] 无法获取 {coin} 的市价"
                        logger.error(error_msg)
                        return {"status": "err", "response": error_msg}
                
                # 3. 计算保证金：保证金 = (size * price) / leverage
                effective_leverage = leverage if leverage is not None else 1
                position_value = size * actual_price
                required_margin = position_value / effective_leverage
                
                # 4. 保证金要求：使用配置的最小保证金
                min_margin = settings.ai_min_margin
                if required_margin < min_margin:
                    error_msg = (
                        f"❌ [Aster] 保证金不足最小要求\n"
                        f"   仓位价值: ${position_value:.2f}\n"
                        f"   杠杆: {effective_leverage}x\n"
                        f"   所需保证金: ${required_margin:.2f}\n"
                        f"   最小保证金: ${min_margin:.2f} (配置: AI_MIN_MARGIN={settings.ai_min_margin})"
                    )
                    logger.error(error_msg)
                    return {"status": "err", "response": error_msg}
                
                logger.info(
                    f"[Aster] ✅ 风控检查通过 - "
                    f"杠杆: {effective_leverage}x, "
                    f"保证金: ${required_margin:.2f} (最小: ${min_margin})"
                )
            
            # 如果指定了杠杆，先设置杠杆（必须成功，否则不下单）
            if leverage is not None and not reduce_only:
                try:
                    logger.info(f"[Aster] 🎯 准备设置杠杆: {coin} -> {leverage}x")
                    leverage_result = await self.update_leverage_async(coin, leverage)
                    logger.info(f"[Aster] ✅ 杠杆设置成功: {leverage}x, 返回: {leverage_result}")
                    
                    # 验证杠杆是否真的设置成功
                    if isinstance(leverage_result, dict):
                        actual_leverage = leverage_result.get('leverage')
                        if actual_leverage and int(actual_leverage) != leverage:
                            logger.warning(f"⚠️ [Aster] 杠杆设置值不匹配: 期望{leverage}x, 实际{actual_leverage}x")
                except Exception as e:
                    error_msg = f"❌ [Aster] 设置杠杆失败，取消下单操作: {e}"
                    logger.error(error_msg)
                    return {"status": "err", "response": error_msg}
            
            # 转换币种格式
            symbol = f"{coin}USDT" if not coin.endswith('USDT') else coin
            
            # 使用统一的精度配置处理数量
            size_rounded, _ = precision_config.format_aster_quantity(
                coin, size, round_down=(not reduce_only)
            )
            
            # 🔍 重要：精度舍入后重新检查保证金
            if not reduce_only and leverage is not None:
                # 使用舍入后的数量重新计算保证金
                final_position_value_check = size_rounded * actual_price
                final_margin_check = final_position_value_check / leverage
                min_margin = settings.ai_min_margin  # 使用环境配置
                
                if final_margin_check < min_margin:
                    # 精度舍入导致保证金不足，需要增加数量
                    logger.warning(
                        f"⚠️ [Aster] 精度舍入后保证金不足，调整数量\n"
                        f"   原始数量: {size:.6f}\n"
                        f"   舍入数量: {size_rounded:.6f}\n"
                        f"   舍入后保证金: ${final_margin_check:.2f}\n"
                        f"   最小保证金: ${min_margin:.2f} (配置: AI_MIN_MARGIN)"
                    )
                    
                    # 重新计算满足最小保证金的数量
                    required_position_value = min_margin * leverage
                    size_rounded = required_position_value / actual_price
                    
                    # 再次应用精度（这次向上舍入以确保满足最小保证金）
                    size_rounded, _ = precision_config.format_aster_quantity(
                        coin, size_rounded, round_down=False  # 向上舍入
                    )
                    
                    # 最终验证
                    final_check_value = size_rounded * actual_price
                    final_check_margin = final_check_value / leverage
                    logger.info(
                        f"   ✅ 调整完成\n"
                        f"   调整后数量: {size_rounded:.6f}\n"
                        f"   调整后保证金: ${final_check_margin:.2f}"
                    )
            
            # 处理价格
            if price is None:
                # 市价单
                orderbook = await self.get_orderbook(coin)
                bids = orderbook.get("bids", [])
                asks = orderbook.get("asks", [])
                
                if is_buy:
                    price = float(asks[0][0]) if asks else None
                else:
                    price = float(bids[0][0]) if bids else None
                
                if price is None:
                    raise ValueError(f"无法获取 {coin} 的市价")
                
                logger.info(f"[Aster] 市价单价格: ${price:,.2f}")
            
            # 使用统一的精度配置处理价格
            price_rounded, _ = precision_config.format_aster_price(coin, price)
            
            # 验证订单参数
            is_valid, error_msg = precision_config.validate_aster_order(coin, size_rounded, price_rounded)
            if not is_valid:
                raise ValueError(f"订单参数验证失败: {error_msg}")
            
            # 最终订单信息
            final_position_value = size_rounded * (price_rounded or actual_price)
            final_margin = final_position_value / effective_leverage if effective_leverage > 0 else final_position_value
            
            logger.info("=" * 70)
            logger.info(f"[Aster] 📊 最终下单参数:")
            logger.info(f"   交易对: {symbol}")
            logger.info(f"   方向: {'买入(做多)' if is_buy else '卖出(做空)'}")
            logger.info(f"   数量: {size_rounded} {coin}")
            logger.info(f"   价格: ${price_rounded if price_rounded else actual_price:,.2f}")
            logger.info(f"   🎯 杠杆: {effective_leverage}x")
            logger.info(f"   💰 预期保证金: ${final_margin:.2f}")
            logger.info(f"   📊 预期仓位价值: ${final_position_value:.2f}")
            logger.info("=" * 70)
            
            # 构建订单请求 (AsterDex V3 格式)
            order_params = {
                "symbol": symbol,
                "positionSide": "BOTH",  # 单向持仓模式
                "side": "BUY" if is_buy else "SELL",
                "type": "LIMIT" if order_type == "Limit" else "MARKET",
                "quantity": str(size_rounded),
                "reduceOnly": reduce_only
            }
            
            # 市价单不需要 price 和 timeInForce
            if order_type == "Limit":
                order_params["price"] = price_rounded  # 已按照API规范处理精度
                order_params["timeInForce"] = "GTC" if not reduce_only else "IOC"
            
            # 调试：打印订单参数
            logger.info(f"[Aster] 🔍 订单参数: {order_params}")
            
            # 发送订单请求 (使用 V3 端点)
            result = await self._request("POST", "/fapi/v3/order", params=order_params, signed=True)
            
            logger.info(f"[Aster] 📝 订单结果: {result}")
            
            # 标准化返回格式
            if result.get('orderId'):
                return {
                    "status": "ok",
                    "response": {
                        "data": {
                            "statuses": [{
                                "filled": {
                                    "oid": result.get('orderId')
                                }
                            }]
                        }
                    },
                    "raw": result
                }
            else:
                return {"status": "err", "response": result}
            
        except Exception as e:
            logger.error(f"[Aster] ❌ 下单失败: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return {"status": "err", "response": str(e)}
    
    async def cancel_order(self, coin: str, order_id: str) -> Dict:
        """取消订单"""
        try:
            symbol = f"{coin}USDT" if not coin.endswith('USDT') else coin
            result = await self._request(
                "DELETE",
                "/fapi/v3/order",  # 使用 v3 端点（v1 在 Aster 上需要签名时会返回 401）
                params={"symbol": symbol, "orderId": order_id},
                signed=True
            )
            return result
        except Exception as e:
            logger.error(f"[Aster] 取消订单失败: {e}")
            return {"status": "err", "response": str(e)}
    
    async def get_open_orders(self, coin: str = None) -> List[Dict]:
        """获取未成交订单"""
        try:
            params = {}
            if coin:
                symbol = f"{coin}USDT" if not coin.endswith('USDT') else coin
                params["symbol"] = symbol
            
            # 使用 v3 端点（v1 在 Aster 上需要签名时会返回 401）
            result = await self._request("GET", "/fapi/v3/openOrders", params=params, signed=True)
            return result if isinstance(result, list) else []
        except Exception as e:
            logger.error(f"[Aster] 获取未成交订单失败: {e}")
            return []
    
    async def get_user_fills(self, limit: int = 100, start_time_ms: int = None) -> List[Dict]:
        """获取用户历史成交记录"""
        try:
            params = {"limit": limit}
            if start_time_ms:
                params["startTime"] = start_time_ms
            
            # 使用 v3 端点（v1 在 Aster 上需要签名时会返回 401）
            result = await self._request("GET", "/fapi/v3/userTrades", params=params, signed=True)
            
            fills = result if isinstance(result, list) else []
            logger.info(f"[Aster] 📊 获取了 {len(fills)} 条历史成交记录")
            return fills
        except Exception as e:
            logger.error(f"[Aster] 获取历史成交失败: {e}")
            return []
    
    async def get_candles(
        self,
        coin: str,
        interval: str = "15m",
        lookback: int = 100,
        timeout: int = 30
    ) -> List[Dict]:
        """获取 K 线数据"""
        async def _fetch_candles():
            symbol = f"{coin}USDT" if not coin.endswith('USDT') else coin
            params = {
                "symbol": symbol,
                "interval": interval,
                "limit": lookback
            }
            result = await self._request("GET", "/fapi/v1/klines", params=params)
            
            # 转换 AsterDex K线格式
            # [openTime, open, high, low, close, volume, closeTime, ...]
            candles = []
            if isinstance(result, list):
                for candle in result:
                    candles.append({
                        "time": int(candle[0]),  # openTime (毫秒)
                        "open": float(candle[1]),
                        "high": float(candle[2]),
                        "low": float(candle[3]),
                        "close": float(candle[4]),
                        "volume": float(candle[5])
                    })
            
            logger.info(f"[Aster] 📊 获取了 {len(candles)} 根 {interval} K线数据")
            return candles
        
        try:
            candles = await asyncio.wait_for(_fetch_candles(), timeout=timeout)
            return candles
        except asyncio.TimeoutError:
            logger.warning(f"[Aster] ⚠️  获取K线数据超时（{timeout}秒）")
            return []
        except Exception as e:
            logger.warning(f"[Aster] ⚠️  获取K线数据失败: {e}")
            return []
    
    async def close_session(self):
        """关闭会话"""
        if self.session and not self.session.closed:
            await self.session.close()
            logger.info("[Aster] ✅ 会话已关闭")
