# 评分模型

## 稳定刷分推荐

目标：在 `mulPoint = 4` 的代币中，优先找出更适合稳定刷分的标的。

综合以下维度：

- `24h volume`：成交额越高越好
- `liquidity`：流动性越高越好
- `holders`：持有人越多越好
- `realized volatility`：短周期波动越低越好
- `4h amplitude`：近 4 小时振幅越低越好
- `audit risk`：审计风险越低越好

推荐分数范围：`0-100`

默认权重：

- 成交额 `25`
- 流动性 `20`
- 持有人 `15`
- 短周期波动反向分 `20`
- 4h 振幅反向分 `10`
- 审计分 `10`

## 合约异动通知

目标：在 Alpha 币已上线 U 本位合约的集合中，挑出最值得提醒的标的。

综合以下维度：

- `24h abs(priceChangePercent)`
- `quoteVolume`
- `abs(lastFundingRate)`
- `abs(openInterestChange5mPct)`

默认思路：

- 先按价格变化、成交额、资金费率做预筛
- 再对 Top 候选补抓 `openInterest` 与 `openInterestHist`
- 最终给出通知候选和触发原因

## 参与人数估算

公式：

```text
estimated_participants = total_quadruple_points_volume_24h / participant_volume_standard
```

默认 `participant_volume_standard = 8200`。

这个值是显式假设，不代表官方真实人数统计。
