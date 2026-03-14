from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path


def fmt_money(value: float) -> str:
    amount = float(value or 0)
    if abs(amount) >= 1_000_000_000:
        return f"${amount / 1_000_000_000:.2f}B"
    if abs(amount) >= 1_000_000:
        return f"${amount / 1_000_000:.2f}M"
    if abs(amount) >= 1_000:
        return f"${amount / 1_000:.2f}K"
    return f"${amount:.2f}"


def fmt_pct(value: float) -> str:
    amount = float(value or 0)
    sign = "+" if amount > 0 else ""
    return f"{sign}{amount:.2f}%"


def load_report(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8", newline="\n")


def build_form_answers(report: dict) -> str:
    top_stable = report["stable_candidates"]["recommendations"][0]
    top_future = report["futures_alerts"]["alerts"][0]
    summary = report["daily_brief"]["summary"]
    generated_at = report["generated_at"]
    participant_standard = report["assumptions"]["participant_volume_standard"]
    return f"""# 报名表填写建议（可直接复制）

## 1. 请给您的小龙虾/产品取一个名称

币安 Alpha 助手

## 2. 您希望解决什么币安相关的问题？/达成什么目标？

币安 Alpha 助手聚焦 Binance Alpha 用户最常见的信息断层问题：一是难以及时识别四倍分代币并判断当前竞争强度，二是难以快速筛出更适合稳定刷分的标的，三是难以同步发现 Alpha 区已上线 U 本位合约的高波动机会与风险，四是难以把 Alpha 变化与币安官方上新、新闻、活动整合成一份可执行日报。

这个 AI Agent 会自动聚合 Binance Alpha、Alpha Trade、Binance Futures 与 Binance 官方公告多源数据，输出四倍分成交额统计、按 {participant_standard} / 人标准的参与人数估算、稳定刷分推荐、Alpha 合约异动提醒和官方 Alpha 日报，帮助用户降低手动盯盘和信息整理成本，提高在 Binance 生态中的决策效率。

截至 {generated_at} 的演示结果中，系统已成功识别 {report['quadruple_points']['token_count']} 个四倍分代币，四倍分 24h 总成交额约 {fmt_money(report['quadruple_points']['total_volume_24h'])}，估算参与人数约 {report['quadruple_points']['estimated_participants']:.0f}；当前稳定刷分首选为 {top_stable['symbol']}，当前重点合约异动候选为 {top_future['alpha_symbol']} / {top_future['futures_symbol']}。

## 3. 请上传您在 X 或者币安广场宣传您“小龙虾”的链接

先发布下列宣传文案，然后把实际链接粘贴到这里：

- X 链接：`<发布后粘贴实际链接>`
- 币安广场链接：`<发布后粘贴实际链接>`

## 4. 提交展示视频、图文说明具体方案展示您的小龙虾如何工作/你的产品如何工作

建议上传以下 5 个文件：

- `submission/assets/binance_alpha_assistant_submission.pdf`
- `submission/assets/demo-overview.png`
- `submission/assets/demo-stable.png`
- `submission/assets/demo-futures.png`
- `submission/assets/demo-daily.png`

## 5. 提供 Link 可访问的在线 Demo，也可以附加提交 GitHub 仓库（可选）

推荐填写：

- 在线 Demo：`<你的 GitHub Pages / Vercel / Netlify 链接>`
- GitHub 仓库：`<你的 GitHub 仓库链接>`

如果来不及部署在线 Demo，至少提交 GitHub 仓库，并在仓库 README 中说明如何本地运行 `demo/index.html`。

## 6. 如果入选，您是否愿意参与币安广场的小龙虾项目宣讲直播？

推荐填写：愿意

## 7. 请留下您的有效联系方式（TG、X、邮箱等提交一种即可）

推荐填写其中一种：

- TG：`@你的TG`
- X：`@你的X`
- 邮箱：`your@email.com`

## 8. 填写推荐人的币安UID（如有）

- 有推荐人：填写对方 UID
- 没有推荐人：留空

## 推荐补充亮点（可用于表单备注或图文说明）

- 四倍分识别基于 Binance Alpha 官方 `mulPoint` 字段，不靠手工维护名单。
- 刷分推荐不是只看涨跌，而是同时考虑成交额、流动性、持有人、短周期波动和审计风险。
- 合约异动模块会把 Alpha 币与 Binance U 本位合约联动分析，输出更适合提醒的标的。
- Alpha 日报整合官方上新、官方新闻、官方活动，减少用户的信息切换成本。
- 当前日报摘要示例：{'; '.join(summary)}
"""


def build_x_post(report: dict) -> str:
    top_stable = report["stable_candidates"]["recommendations"][0]["symbol"]
    top_future = report["futures_alerts"]["alerts"][0]
    return (
        "参赛作品：《币安 Alpha 助手》\n\n"
        "一个面向 Binance Alpha 的 AI Agent：\n"
        "1. 自动统计四倍分代币总成交额，并按 8200 / 人估算参与人数\n"
        f"2. 识别更适合稳定刷分的代币，当前演示首选 {top_stable}\n"
        f"3. 监控 Alpha 关联 U 本位合约异动，当前重点候选 {top_future['alpha_symbol']} / {top_future['futures_symbol']}\n"
        "4. 生成含官方上新 / 新闻 / 活动的 Alpha 日报\n\n"
        "Demo：<在线 Demo 链接>\n"
        "GitHub：<GitHub 仓库链接>\n"
        "#Binance #OpenClaw #BinanceAlpha"
    )


def build_square_post(report: dict) -> str:
    return (
        "参赛作品：币安 Alpha 助手\n\n"
        "这是一个围绕 Binance Alpha 场景打造的 AI Agent，目标是降低 Alpha 用户的信息整理成本和手动盯盘成本。\n\n"
        "核心能力：\n"
        "- 自动识别四倍分代币，并统计总成交额\n"
        "- 按 8200 / 人估算当前参与人数\n"
        "- 结合流动性、成交额、持有人、短周期波动与审计结果，推荐更适合稳定刷分的代币\n"
        "- 统计 Alpha 相关 U 本位合约，筛出值得通知的异动标的\n"
        "- 自动生成整合官方上新、新闻、活动的 Alpha 日报\n\n"
        "作品定位：交易辅助 + 用户服务 + 运营工具\n"
        "Demo：<在线 Demo 链接>\n"
        "GitHub：<GitHub 仓库链接>"
    )


def build_demo_script(report: dict) -> str:
    top_stable = report["stable_candidates"]["recommendations"][0]
    top_future = report["futures_alerts"]["alerts"][0]
    return f"""# 录屏脚本（90 秒版本）

## 开场（0-15 秒）

大家好，我的参赛作品叫《币安 Alpha 助手》，它是一个面向 Binance Alpha 的 AI Agent，帮助用户更快识别四倍分机会、稳定刷分标的、合约异动和官方动态。

## 四倍分面板（15-35 秒）

这里先看四倍分总览。系统直接读取 Binance Alpha 官方列表里的 `mulPoint` 字段，自动筛出四倍分代币，统计总成交额，并按 8200 / 人估算当前参与人数。这样用户不用手工统计，也能快速判断当前 Alpha 竞争强度。

## 稳定刷分推荐（35-55 秒）

接着看稳定刷分推荐。这个模块不会只看涨跌，而是综合成交额、流动性、持有人、短周期波动、4 小时振幅和审计风险。当前演示里，首选代币是 {top_stable['symbol']}，因为它在流动性和成交额上更强，同时短周期波动更可控。

## 合约异动（55-75 秒）

再看 Alpha 合约异动模块。系统会把 Alpha 币和 Binance U 本位合约联动起来，结合 24 小时涨跌、成交额、资金费率和持仓变化，挑出值得提醒的标的。当前演示中，重点候选是 {top_future['alpha_symbol']} / {top_future['futures_symbol']}。

## 官方日报（75-90 秒）

最后是 Alpha 日报。系统会自动整合币安官方上新、官方新闻和官方活动，再结合 Alpha 最新上线信息生成日报，帮助用户用一页内容快速掌握当日重点。
"""


def build_upload_manifest() -> str:
    return """# 提交清单

## 表单第 3 题：先发布再回填链接

- `submission/x_post_draft_zh.txt`
- `submission/square_post_draft_zh.txt`

## 表单第 4 题：建议上传这些文件

- `submission/assets/binance_alpha_assistant_submission.pdf`
- `submission/assets/demo-overview.png`
- `submission/assets/demo-stable.png`
- `submission/assets/demo-futures.png`
- `submission/assets/demo-daily.png`

## 表单第 5 题：建议提供这些链接

- 在线 Demo 链接：GitHub Pages / Vercel / Netlify
- GitHub 仓库链接

## 仍需你手动补充的信息

- X 或币安广场实际帖子链接
- 你的联系方式
- 推荐人 UID（如有）
- 你的 GitHub 仓库地址
- 在线 Demo 地址（如部署）
"""


def build_brief_html(report: dict) -> str:
    top_stable = report["stable_candidates"]["recommendations"][0]
    top_future = report["futures_alerts"]["alerts"][0]
    summary_items = "".join(f"<li>{item}</li>" for item in report["daily_brief"]["summary"])
    return f"""<!doctype html>
<html lang='zh-CN'>
<head>
  <meta charset='utf-8'>
  <title>币安 Alpha 助手 - 提交说明</title>
  <style>
    body{{font-family:Arial,'Microsoft YaHei',sans-serif;background:#fff;color:#111;line-height:1.6;margin:0}}
    .wrap{{max-width:980px;margin:0 auto;padding:32px}}
    h1,h2{{margin:0 0 12px}} .muted{{color:#666}} .card{{border:1px solid #ddd;border-radius:14px;padding:16px;margin:14px 0}}
    .grid{{display:grid;grid-template-columns:repeat(2,1fr);gap:14px}} .kpis{{display:grid;grid-template-columns:repeat(4,1fr);gap:12px}}
    .kpi{{border:1px solid #ddd;border-radius:12px;padding:14px}} .v{{font-size:28px;font-weight:700}}
    img{{width:100%;border:1px solid #ddd;border-radius:12px}} ul{{margin:8px 0 0}}
  </style>
</head>
<body>
<div class='wrap'>
  <h1>币安 Alpha 助手</h1>
  <div class='muted'>Binance Alpha 赛道的 AI Agent：四倍分跟踪 / 稳定刷分推荐 / 合约异动 / 官方日报</div>

  <div class='kpis'>
    <div class='kpi'><div class='muted'>四倍分代币数</div><div class='v'>{report['quadruple_points']['token_count']}</div></div>
    <div class='kpi'><div class='muted'>四倍分 24h 总成交额</div><div class='v'>{fmt_money(report['quadruple_points']['total_volume_24h'])}</div></div>
    <div class='kpi'><div class='muted'>估算参与人数</div><div class='v'>{report['quadruple_points']['estimated_participants']:.0f}</div></div>
    <div class='kpi'><div class='muted'>Alpha 对应合约数</div><div class='v'>{report['futures_alerts']['matched_contract_count']}</div></div>
  </div>

  <div class='card'>
    <h2>产品要解决的问题</h2>
    <p>币安 Alpha 用户往往要在多个页面之间来回切换，才能知道哪些是四倍分、当前竞争强度如何、哪些币更适合稳定刷分、哪些 Alpha 相关合约正在异动，以及最近币安官方又有哪些上新和活动。币安 Alpha 助手把这些数据自动整合成一套可直接执行的日报和看板。</p>
  </div>

  <div class='card'>
    <h2>核心能力</h2>
    <ul>
      <li>自动识别 Binance Alpha 官方四倍分代币，并统计总成交额</li>
      <li>按 8200 / 人标准估算参与人数，帮助判断竞争强度</li>
      <li>结合成交额、流动性、持有人、波动和审计结果，推荐更适合稳定刷分的代币</li>
      <li>联动 Binance U 本位合约，筛出需要提醒的异动标的</li>
      <li>自动生成包含官方上新、官方新闻和官方活动的 Alpha 日报</li>
    </ul>
  </div>

  <div class='card'>
    <h2>当前演示结论</h2>
    <ul>
      <li>稳定刷分首选：{top_stable['symbol']}</li>
      <li>重点合约异动：{top_future['alpha_symbol']} / {top_future['futures_symbol']}</li>
      {summary_items}
    </ul>
  </div>

  <div class='grid'>
    <div><img src='./assets/demo-overview.png'><div class='muted'>四倍分总览</div></div>
    <div><img src='./assets/demo-stable.png'><div class='muted'>稳定刷分推荐</div></div>
    <div><img src='./assets/demo-futures.png'><div class='muted'>合约异动</div></div>
    <div><img src='./assets/demo-daily.png'><div class='muted'>Alpha 日报</div></div>
  </div>

  <div class='card'>
    <h2>OpenClaw / GitHub 复用方式</h2>
    <p>项目支持一键生成 JSON、Markdown 和 HTML 三种输出。其他 OpenClaw 或 Agent 可以直接消费 JSON 结果；GitHub 用户可以直接展示 HTML demo 或接入 GitHub Pages。</p>
  </div>
</div>
</body>
</html>
"""


def main() -> int:
    base_dir = Path(__file__).resolve().parent.parent
    report_path = base_dir / "demo" / "sample_report.json"
    submission_dir = base_dir / "submission"
    submission_assets_dir = submission_dir / "assets"
    submission_assets_dir.mkdir(parents=True, exist_ok=True)
    report = load_report(report_path)
    write(submission_dir / "form_answers_zh.md", build_form_answers(report))
    write(submission_dir / "x_post_draft_zh.txt", build_x_post(report))
    write(submission_dir / "square_post_draft_zh.txt", build_square_post(report))
    write(submission_dir / "demo_script_zh.md", build_demo_script(report))
    write(submission_dir / "upload_manifest.md", build_upload_manifest())
    write(submission_dir / "submission_brief.html", build_brief_html(report))
    print(f"Submission pack generated in {submission_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
