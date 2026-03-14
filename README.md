# 币安 Alpha 助手

一个可提交到 GitHub、可直接给 OpenClaw 复用、并带演示界面的 Binance Alpha skill。

## 解决的问题

- 统计 `mulPoint = 4` 的 Alpha 代币总成交量
- 按 `8200 / 人` 估算当前参与人数
- 计算四倍分代币波动，筛出更适合稳定刷分的标的
- 统计 Alpha 区关联的 U 本位合约，选出高波动预警标的
- 生成带官方来源的 Alpha 日报，覆盖上新、新闻、活动和最近 Alpha 新币

## 目录结构

- `SKILL.md`：OpenClaw 使用说明
- `agents/openai.yaml`：界面元数据
- `scripts/binance_alpha_assistant.py`：主脚本
- `assets/report_template.html`：HTML 仪表盘模板
- `references/data-sources.md`：数据源说明
- `references/scoring-model.md`：评分模型说明
- `config.example.json`：默认配置
- `demo/`：示例输出目录

## 安装依赖

```powershell
py -3 -m pip install -r requirements.txt
```

## 生成实时报告

```powershell
py -3 scripts/binance_alpha_assistant.py \
  --config config.example.json \
  --json-output output/latest_report.json \
  --markdown-output output/latest_report.md \
  --html-output output/latest_report.html
```

## 生成演示文件

```powershell
py -3 scripts/binance_alpha_assistant.py \
  --config config.example.json \
  --json-output demo/sample_report.json \
  --markdown-output demo/sample_report.md \
  --html-output demo/index.html
```

## OpenClaw 复用方式

建议在其他 OpenClaw 中直接执行脚本并读取 JSON：

```powershell
py -3 scripts/binance_alpha_assistant.py --json-output output/latest_report.json
```
