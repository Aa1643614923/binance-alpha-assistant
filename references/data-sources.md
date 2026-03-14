# 数据源说明

## 1. Binance Alpha 官方列表

- Endpoint: `https://www.binance.com/bapi/defi/v1/public/wallet-direct/buw/wallet/cex/alpha/all/token/list`
- 用途：
  - 识别 `mulPoint`
  - 获取 `volume24h`、`liquidity`、`holders`、`listingTime`
  - 获取 `alphaId` 与交易用基础标识

关键字段：

- `mulPoint`：倍数，`4` 即四倍分
- `volume24h`：24h 成交额
- `percentChange24h`：24h 涨跌幅
- `priceHigh24h` / `priceLow24h`：24h 高低点
- `liquidity`：流动性
- `holders`：持有人数量
- `listingTime`：上线时间

## 2. Binance Alpha 交易接口

- Exchange Info: `https://www.binance.com/bapi/defi/v1/public/alpha-trade/get-exchange-info`
- Klines: `https://www.binance.com/bapi/defi/v1/public/alpha-trade/klines`

用途：

- 把 `alphaId` 映射成可交易的 `symbol`
- 计算短周期波动、振幅、趋势

## 3. Binance Web3 审计接口

- Endpoint: `https://web3.binance.com/bapi/defi/v1/public/wallet-direct/security/token/audit`

用途：

- 获取风险等级
- 获取 `buyTax` / `sellTax`
- 识别是否支持审计

## 4. Binance USDS-M Futures 公共接口

- Exchange Info: `https://fapi.binance.com/fapi/v1/exchangeInfo`
- 24h Ticker: `https://fapi.binance.com/fapi/v1/ticker/24hr`
- Premium Index: `https://fapi.binance.com/fapi/v1/premiumIndex`
- Open Interest: `https://fapi.binance.com/fapi/v1/openInterest`
- Open Interest History: `https://fapi.binance.com/futures/data/openInterestHist`

用途：

- 判断 Alpha 币是否已经有 U 本位合约
- 追踪涨跌幅、成交额、资金费率、持仓变化

## 5. Binance 官方公告 CMS 接口

- 列表：`https://www.binance.com/bapi/composite/v1/public/cms/article/list/query?type=1&pageNo=1&pageSize=50`
- 详情：`https://www.binance.com/bapi/composite/v1/public/cms/article/detail/query?articleCode=...`

推荐关注的栏目：

- `48`：New Cryptocurrency Listing
- `49`：Latest Binance News
- `93`：Latest Activities

用途：

- Alpha 日报的官方“上新 / 新闻 / 活动”来源
- 为每条日报保留标题、发布时间和详情链接
