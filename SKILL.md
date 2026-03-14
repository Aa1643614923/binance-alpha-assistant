---
name: binance-alpha-assistant
description: Generate reusable Binance Alpha reports for 4x-point tokens, stable farming candidates, Alpha-linked futures alerts, and official daily briefs. Use this skill when users ask for Binance Alpha point multipliers, "四倍分" token analysis, low-volatility刷分 recommendations, Alpha futures monitoring, or an Alpha日报 with official listings/news/activity sources.
---

# 币安 Alpha 助手

## Overview

这个 skill 面向「币安 Alpha 四倍分跟踪 + 稳定刷币 + 合约异动 + 官方日报」场景。

优先通过本地脚本生成结构化报告，再基于报告回答用户；这样更适合 OpenClaw 复用、GitHub 提交和比赛演示。

## Core Workflow

1. 运行 `scripts/binance_alpha_assistant.py` 生成最新报告。
2. 优先读取生成的 `JSON` 作为结构化事实来源。
3. 面向用户展示时，优先使用 `Markdown` 或 `HTML` 报告。
4. 如果网络不可用，明确说明并回退到已有缓存或示例报告，不要把示例数据说成实时数据。

## What This Skill Produces

脚本会生成三份输出：

- `JSON`：适合其他 OpenClaw / Agent 直接接入复用
- `Markdown`：适合直接贴给用户或发群
- `HTML`：适合录屏演示和比赛展示

## When To Use

当用户提出以下需求时，应触发本 skill：

- 统计 Binance Alpha 里 `mulPoint = 4` 的代币和总成交量
- 按「每人刷 `8200`」估算当前参与人数
- 找波动更稳、流动性更好的「稳定刷分」代币
- 看 Alpha 区哪些币已经有 U 本位合约，并挑出波动大/资金费率异常/持仓变化明显的标的
- 生成 Alpha 日报，汇总官方上新、新闻、活动和最近 Alpha 新币变化

## Runbook

### 1. Generate a fresh report

在 skill 根目录运行：

```powershell
py -3 scripts/binance_alpha_assistant.py \
  --config config.example.json \
  --json-output output/latest_report.json \
  --markdown-output output/latest_report.md \
  --html-output output/latest_report.html
```

### 2. Reuse the JSON first

回答时优先读取 `output/latest_report.json`，不要重复猜测或手算。

### 3. Use the right output for the right audience

- 给用户快读结论：读 `Markdown`
- 做演示或录屏：打开 `HTML`
- 给其他 Agent / OpenClaw：消费 `JSON`

## Behavior Rules

- 只把 `mulPoint == 4` 识别为「四倍分」；不要自行脑补倍数
- 参与人数估算必须显式写明使用的标准值，默认是 `8200`
- 当公告/活动内容来自官方分类接口时，要保留来源链接
- 当某个板块接口失败时，只跳过该板块并记录 warning，不要让整份报告失败
- 如果用户要求“最新”“今天”“最近”，优先重新生成报告，不要依赖旧缓存

## Bundled Resources

### `scripts/`

- `binance_alpha_assistant.py`：主脚本，抓取 Binance Alpha / Futures / Official CMS 数据并生成报告

### `references/`

- `data-sources.md`：官方数据源与字段说明
- `scoring-model.md`：稳定刷分和合约异动的评分方法

### `assets/`

- `report_template.html`：自包含演示页面模板
