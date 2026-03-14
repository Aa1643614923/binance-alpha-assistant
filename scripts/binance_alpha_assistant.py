from __future__ import annotations

import argparse
import json
import math
import statistics
import sys
import time
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Callable, Dict, Iterable, List, Optional

import requests

ALPHA_TOKEN_LIST_URL = "https://www.binance.com/bapi/defi/v1/public/wallet-direct/buw/wallet/cex/alpha/all/token/list"
ALPHA_EXCHANGE_INFO_URL = "https://www.binance.com/bapi/defi/v1/public/alpha-trade/get-exchange-info"
ALPHA_KLINES_URL = "https://www.binance.com/bapi/defi/v1/public/alpha-trade/klines"
TOKEN_AUDIT_URL = "https://web3.binance.com/bapi/defi/v1/public/wallet-direct/security/token/audit"
FUTURES_EXCHANGE_INFO_URL = "https://fapi.binance.com/fapi/v1/exchangeInfo"
FUTURES_TICKER_24H_URL = "https://fapi.binance.com/fapi/v1/ticker/24hr"
FUTURES_PREMIUM_INDEX_URL = "https://fapi.binance.com/fapi/v1/premiumIndex"
FUTURES_OPEN_INTEREST_URL = "https://fapi.binance.com/fapi/v1/openInterest"
FUTURES_OPEN_INTEREST_HIST_URL = "https://fapi.binance.com/futures/data/openInterestHist"
CMS_ARTICLE_LIST_URL = "https://www.binance.com/bapi/composite/v1/public/cms/article/list/query"
CMS_ARTICLE_DETAIL_URL = "https://www.binance.com/bapi/composite/v1/public/cms/article/detail/query"

DEFAULT_CONFIG: Dict[str, Any] = {
    "participant_volume_standard": 8200,
    "request_timeout_seconds": 20,
    "request_interval_seconds": 0.08,
    "alpha_kline_interval": "5m",
    "alpha_kline_limit": 48,
    "stable_limit": 5,
    "futures_probe_limit": 12,
    "futures_alert_limit": 8,
    "announcement_limit_per_catalog": 3,
    "recent_listing_hours": 72,
    "announcement_catalog_ids": [48, 49, 93],
    "stable_thresholds": {"min_volume24h": 500000, "min_liquidity": 150000},
    "futures_thresholds": {
        "min_abs_price_change_pct": 8,
        "min_quote_volume": 5000000,
        "min_abs_oi_change_pct": 0.5,
        "min_abs_funding_bps": 1.0,
    },
}


def ensure_utf8_stdout() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8")


def to_float(value: Any) -> Optional[float]:
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        text = value.strip().replace(",", "")
        if not text:
            return None
        try:
            return float(text)
        except ValueError:
            return None
    return None


def to_int(value: Any) -> Optional[int]:
    if value is None:
        return None
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    if isinstance(value, str):
        text = value.strip().replace(",", "")
        if not text:
            return None
        try:
            return int(float(text))
        except ValueError:
            return None
    return None


def clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def utc_iso_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def ts_to_iso(timestamp_ms: Any) -> Optional[str]:
    value = to_int(timestamp_ms)
    if value is None or value <= 0:
        return None
    return datetime.fromtimestamp(value / 1000, tz=timezone.utc).isoformat()


def merge_dicts(base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
    merged = dict(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = merge_dicts(merged[key], value)
        else:
            merged[key] = value
    return merged


def load_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    raw = path.read_text(encoding="utf-8").lstrip("\ufeff")
    if not raw.strip():
        return default
    return json.loads(raw)


def save_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def save_json(path: Path, payload: Any) -> None:
    save_text(path, json.dumps(payload, ensure_ascii=False, indent=2))


def min_max_scale(values: List[Optional[float]], value: Optional[float]) -> float:
    filtered = [item for item in values if item is not None]
    if value is None or not filtered:
        return 0.5
    low, high = min(filtered), max(filtered)
    if math.isclose(low, high):
        return 0.5
    return clamp((value - low) / (high - low), 0.0, 1.0)


def safe_first(items: Iterable[Any]) -> Any:
    for item in items:
        return item
    return None


def extract_text_segments(node: Any) -> List[str]:
    if isinstance(node, dict):
        if node.get("node") == "text":
            text = str(node.get("text") or "").strip()
            return [text] if text else []
        output: List[str] = []
        for child in node.get("child") or []:
            output.extend(extract_text_segments(child))
        return output
    if isinstance(node, list):
        output: List[str] = []
        for child in node:
            output.extend(extract_text_segments(child))
        return output
    return []


def body_json_to_summary(raw_body: Any, max_chars: int = 180) -> str:
    if not raw_body:
        return ""
    try:
        payload = json.loads(raw_body) if isinstance(raw_body, str) else raw_body
    except json.JSONDecodeError:
        return str(raw_body)[:max_chars].strip()
    text = " ".join(segment for segment in extract_text_segments(payload) if segment)
    text = " ".join(text.split())
    return text if len(text) <= max_chars else f"{text[: max_chars - 1].rstrip()}…"


class BinanceApiClient:
    def __init__(self, timeout_seconds: int, interval_seconds: float) -> None:
        self.timeout_seconds = timeout_seconds
        self.interval_seconds = interval_seconds
        self.session = requests.Session()
        self.session.headers.update({"Accept-Encoding": "identity", "User-Agent": "binance-alpha-assistant/1.0"})

    def _sleep(self) -> None:
        if self.interval_seconds > 0:
            time.sleep(self.interval_seconds)

    def _request_json(self, method: str, url: str, *, params: Dict[str, Any] | None = None, body: Dict[str, Any] | None = None, headers: Dict[str, str] | None = None) -> Any:
        response = self.session.request(method=method, url=url, params=params, json=body, headers=headers, timeout=self.timeout_seconds)
        response.raise_for_status()
        self._sleep()
        payload = response.json()
        if isinstance(payload, dict):
            code = str(payload.get("code", ""))
            if code and code != "000000":
                raise RuntimeError(f"request failed code={code} url={url}")
            if payload.get("success") is False:
                raise RuntimeError(f"request failed success=false url={url}")
        return payload

    def get_alpha_tokens(self) -> List[Dict[str, Any]]:
        return (self._request_json("GET", ALPHA_TOKEN_LIST_URL).get("data") or [])

    def get_alpha_exchange_info(self) -> Dict[str, Any]:
        return (self._request_json("GET", ALPHA_EXCHANGE_INFO_URL).get("data") or {})

    def get_alpha_ticker(self, symbol: str) -> Dict[str, Any]:
        payload = self._request_json("GET", "https://www.binance.com/bapi/defi/v1/public/alpha-trade/ticker", params={"symbol": symbol})
        return payload.get("data") or {}

    def get_alpha_klines(self, symbol: str, interval: str, limit: int) -> List[List[Any]]:
        payload = self._request_json("GET", ALPHA_KLINES_URL, params={"symbol": symbol, "interval": interval, "limit": limit})
        return payload.get("data") or []

    def audit_token(self, chain_id: str, contract_address: str) -> Dict[str, Any]:
        payload = self._request_json("POST", TOKEN_AUDIT_URL, body={"binanceChainId": chain_id, "contractAddress": contract_address, "requestId": str(uuid.uuid4())}, headers={"Content-Type": "application/json"})
        return payload.get("data") or {}

    def get_futures_exchange_info(self) -> Dict[str, Any]:
        return self._request_json("GET", FUTURES_EXCHANGE_INFO_URL)

    def get_futures_tickers(self) -> List[Dict[str, Any]]:
        payload = self._request_json("GET", FUTURES_TICKER_24H_URL)
        return payload if isinstance(payload, list) else []

    def get_futures_premium_index(self) -> List[Dict[str, Any]]:
        payload = self._request_json("GET", FUTURES_PREMIUM_INDEX_URL)
        return payload if isinstance(payload, list) else []

    def get_open_interest(self, symbol: str) -> Dict[str, Any]:
        return self._request_json("GET", FUTURES_OPEN_INTEREST_URL, params={"symbol": symbol})

    def get_open_interest_hist(self, symbol: str, period: str = "5m", limit: int = 2) -> List[Dict[str, Any]]:
        payload = self._request_json("GET", FUTURES_OPEN_INTEREST_HIST_URL, params={"symbol": symbol, "period": period, "limit": limit})
        return payload if isinstance(payload, list) else []

    def get_announcement_catalogs(self, page_size: int = 50) -> List[Dict[str, Any]]:
        payload = self._request_json("GET", CMS_ARTICLE_LIST_URL, params={"type": 1, "pageNo": 1, "pageSize": page_size}, headers={"User-Agent": "Mozilla/5.0", "Accept-Encoding": "identity"})
        return (payload.get("data") or {}).get("catalogs") or []

    def get_announcement_detail(self, article_code: str) -> Dict[str, Any]:
        payload = self._request_json("GET", CMS_ARTICLE_DETAIL_URL, params={"articleCode": article_code}, headers={"User-Agent": "Mozilla/5.0", "Accept-Encoding": "identity"})
        return payload.get("data") or {}

class AlphaAssistantBuilder:
    def __init__(self, config: Dict[str, Any]) -> None:
        self.config = config
        self.client = BinanceApiClient(timeout_seconds=to_int(config.get("request_timeout_seconds")) or 20, interval_seconds=to_float(config.get("request_interval_seconds")) or 0.0)
        self.warnings: List[str] = []

    def safe_call(self, label: str, func: Callable[..., Any], *args: Any, fallback: Any = None, **kwargs: Any) -> Any:
        try:
            return func(*args, **kwargs)
        except Exception as exc:
            self.warnings.append(f"{label}: {exc}")
            return fallback

    def build(self) -> Dict[str, Any]:
        alpha_tokens = self.safe_call("alpha_token_list", self.client.get_alpha_tokens, fallback=[])
        alpha_exchange_info = self.safe_call("alpha_exchange_info", self.client.get_alpha_exchange_info, fallback={})
        alpha_symbol_index = self.build_alpha_symbol_index(alpha_exchange_info)
        alpha_symbol_groups = self.build_alpha_symbol_groups(alpha_exchange_info)
        quadruple_points = self.build_quadruple_points(alpha_tokens, alpha_symbol_index, alpha_symbol_groups)
        stable_candidates = self.build_stable_candidates(quadruple_points["tokens"])
        futures_alerts = self.build_futures_alerts(alpha_tokens)
        daily_brief = self.build_daily_brief(alpha_tokens)
        return {
            "skill": "binance-alpha-assistant",
            "generated_at": utc_iso_now(),
            "assumptions": {
                "participant_volume_standard": self.config["participant_volume_standard"],
                "alpha_kline_interval": self.config["alpha_kline_interval"],
                "alpha_kline_limit": self.config["alpha_kline_limit"],
                "recent_listing_hours": self.config["recent_listing_hours"],
            },
            "quadruple_points": quadruple_points,
            "stable_candidates": stable_candidates,
            "futures_alerts": futures_alerts,
            "daily_brief": daily_brief,
            "warnings": self.warnings,
        }

    def build_alpha_symbol_index(self, exchange_info: Dict[str, Any]) -> Dict[str, str]:
        index: Dict[str, List[str]] = {}
        for item in exchange_info.get("symbols") or []:
            base_asset = str(item.get("baseAsset") or "")
            symbol = str(item.get("symbol") or "")
            if not base_asset or not symbol:
                continue
            index.setdefault(base_asset, []).append(symbol)
        preferred: Dict[str, str] = {}
        for base_asset, candidates in index.items():
            preferred[base_asset] = safe_first(symbol for symbol in candidates if symbol.endswith("USDT")) or safe_first(symbol for symbol in candidates if symbol.endswith("USDC")) or candidates[0]
        return preferred

    def build_alpha_symbol_groups(self, exchange_info: Dict[str, Any]) -> Dict[str, List[str]]:
        groups: Dict[str, List[str]] = {}
        for item in exchange_info.get("symbols") or []:
            base_asset = str(item.get("baseAsset") or "")
            symbol = str(item.get("symbol") or "")
            if not base_asset or not symbol:
                continue
            groups.setdefault(base_asset, []).append(symbol)
        return groups

    def build_quadruple_points(self, alpha_tokens: List[Dict[str, Any]], alpha_symbol_index: Dict[str, str], alpha_symbol_groups: Dict[str, List[str]]) -> Dict[str, Any]:
        participant_standard = to_float(self.config.get("participant_volume_standard")) or 8200.0
        rows: List[Dict[str, Any]] = []
        total_token_list_volume = 0.0
        total_alpha_trade_quote_volume = 0.0
        total_alpha_trade_base_volume = 0.0
        for token in alpha_tokens:
            if to_int(token.get("mulPoint")) != 4:
                continue
            token_list_volume24h = to_float(token.get("volume24h")) or 0.0
            price_high = to_float(token.get("priceHigh24h")) or 0.0
            price_low = to_float(token.get("priceLow24h")) or 0.0
            amplitude = ((price_high - price_low) / price_low * 100.0) if price_low > 0 else None
            alpha_id = str(token.get("alphaId") or "")
            alpha_trade_symbols = alpha_symbol_groups.get(alpha_id, [])
            alpha_trade_quote_volume24h = 0.0
            alpha_trade_base_volume24h = 0.0
            alpha_trade_tickers: List[Dict[str, Any]] = []
            for trade_symbol in alpha_trade_symbols:
                ticker = self.safe_call(f"alpha_ticker:{trade_symbol}", self.client.get_alpha_ticker, trade_symbol, fallback={})
                if not ticker:
                    continue
                quote_volume = to_float(ticker.get("quoteVolume")) or 0.0
                base_volume = to_float(ticker.get("volume")) or 0.0
                alpha_trade_quote_volume24h += quote_volume
                alpha_trade_base_volume24h += base_volume
                alpha_trade_tickers.append({
                    "symbol": trade_symbol,
                    "quote_volume24h": quote_volume,
                    "base_volume24h": base_volume,
                    "last_price": to_float(ticker.get("lastPrice")),
                })
            row = {
                "symbol": token.get("symbol"),
                "name": token.get("name"),
                "chain_id": token.get("chainId"),
                "contract_address": token.get("contractAddress"),
                "alpha_id": alpha_id,
                "alpha_trade_symbol": alpha_symbol_index.get(alpha_id),
                "alpha_trade_symbols": alpha_trade_symbols,
                "alpha_trade_tickers": alpha_trade_tickers,
                "mul_point": 4,
                "price": to_float(token.get("price")),
                "percent_change_24h": to_float(token.get("percentChange24h")),
                "volume24h": token_list_volume24h,
                "token_list_volume24h": token_list_volume24h,
                "alpha_trade_quote_volume24h": alpha_trade_quote_volume24h,
                "alpha_trade_base_volume24h": alpha_trade_base_volume24h,
                "liquidity": to_float(token.get("liquidity")) or 0.0,
                "holders": to_int(token.get("holders")) or 0,
                "count24h": to_int(token.get("count24h")) or 0,
                "listing_time": ts_to_iso(token.get("listingTime")),
                "listing_time_ms": to_int(token.get("listingTime")),
                "amplitude_24h_pct": amplitude,
                "estimated_participants": alpha_trade_quote_volume24h / participant_standard if participant_standard > 0 else None,
            }
            rows.append(row)
            total_token_list_volume += token_list_volume24h
            total_alpha_trade_quote_volume += alpha_trade_quote_volume24h
            total_alpha_trade_base_volume += alpha_trade_base_volume24h
        rows.sort(key=lambda item: item["alpha_trade_quote_volume24h"], reverse=True)
        return {
            "token_count": len(rows),
            "total_volume_24h": total_alpha_trade_quote_volume,
            "total_alpha_trade_quote_volume_24h": total_alpha_trade_quote_volume,
            "total_alpha_trade_base_volume_24h": total_alpha_trade_base_volume,
            "total_token_list_volume24h": total_token_list_volume,
            "estimated_participants": total_alpha_trade_quote_volume / participant_standard if participant_standard > 0 else None,
            "volume_method": "alpha_trade_quote_volume_sum",
            "tokens": rows,
        }

    def compute_kline_stats(self, klines: List[List[Any]]) -> Dict[str, Any]:
        closes: List[float] = []
        highs: List[float] = []
        lows: List[float] = []
        for item in klines:
            if len(item) < 5:
                continue
            high_price, low_price, close_price = to_float(item[2]), to_float(item[3]), to_float(item[4])
            if high_price is None or low_price is None or close_price is None:
                continue
            highs.append(high_price)
            lows.append(low_price)
            closes.append(close_price)
        returns: List[float] = []
        for index in range(1, len(closes)):
            previous_close = closes[index - 1]
            if previous_close <= 0:
                continue
            returns.append((closes[index] / previous_close - 1.0) * 100.0)
        realized_volatility = statistics.pstdev(returns) if len(returns) >= 2 else None
        amplitude_4h = None
        trend_4h = None
        if highs and lows and closes and closes[0] > 0:
            amplitude_4h = (max(highs) - min(lows)) / closes[0] * 100.0
            trend_4h = (closes[-1] / closes[0] - 1.0) * 100.0
        return {"realized_volatility_pct": realized_volatility, "amplitude_4h_pct": amplitude_4h, "trend_4h_pct": trend_4h}

    def compute_audit_factor(self, audit: Dict[str, Any]) -> float:
        risk = str(audit.get("riskLevelEnum") or "").upper()
        risk_factor = {"LOW": 1.0, "MID": 0.6, "MEDIUM": 0.6, "HIGH": 0.25}.get(risk, 0.5)
        extra_info = audit.get("extraInfo") or {}
        buy_tax = to_float(extra_info.get("buyTax")) or 0.0
        sell_tax = to_float(extra_info.get("sellTax")) or 0.0
        return clamp(risk_factor - clamp((buy_tax + sell_tax) / 20.0, 0.0, 0.25), 0.0, 1.0)

    def build_stable_reasons(self, token: Dict[str, Any]) -> List[str]:
        reasons = [f"24h 成交额 {token['volume24h']:,.0f}，流动性 {token['liquidity']:,.0f}"]
        if token.get("realized_volatility_pct") is not None:
            reasons.append(f"短周期波动 {token['realized_volatility_pct']:.2f}%")
        if token.get("amplitude_4h_pct") is not None:
            reasons.append(f"4h 振幅 {token['amplitude_4h_pct']:.2f}%")
        reasons.append(f"审计风险 {token.get('audit_risk') or '未知'}")
        return reasons

    def build_stable_candidates(self, quadruple_tokens: List[Dict[str, Any]]) -> Dict[str, Any]:
        analyzed: List[Dict[str, Any]] = []
        thresholds = self.config.get("stable_thresholds") or {}
        min_volume24h = to_float(thresholds.get("min_volume24h")) or 0.0
        min_liquidity = to_float(thresholds.get("min_liquidity")) or 0.0
        interval = str(self.config.get("alpha_kline_interval") or "5m")
        limit = to_int(self.config.get("alpha_kline_limit")) or 48
        for token in quadruple_tokens:
            if (token.get("volume24h") or 0) < min_volume24h or (token.get("liquidity") or 0) < min_liquidity or not token.get("alpha_trade_symbol"):
                continue
            klines = self.safe_call(f"alpha_klines:{token['alpha_trade_symbol']}", self.client.get_alpha_klines, token["alpha_trade_symbol"], interval, limit, fallback=[])
            audit = self.safe_call(f"token_audit:{token['symbol']}", self.client.audit_token, token.get("chain_id"), token.get("contract_address"), fallback={})
            item = {**token, **self.compute_kline_stats(klines)}
            item["audit_risk"] = audit.get("riskLevelEnum")
            item["audit_factor"] = self.compute_audit_factor(audit)
            analyzed.append(item)
        volume_values = [to_float(item.get("volume24h")) for item in analyzed]
        liquidity_values = [to_float(item.get("liquidity")) for item in analyzed]
        holder_values = [to_float(item.get("holders")) for item in analyzed]
        volatility_values = [to_float(item.get("realized_volatility_pct")) for item in analyzed]
        amplitude_values = [to_float(item.get("amplitude_4h_pct")) for item in analyzed]
        for item in analyzed:
            score = (
                min_max_scale(volume_values, to_float(item.get("volume24h"))) * 25
                + min_max_scale(liquidity_values, to_float(item.get("liquidity"))) * 20
                + min_max_scale(holder_values, to_float(item.get("holders"))) * 15
                + (1.0 - min_max_scale(volatility_values, to_float(item.get("realized_volatility_pct")))) * 20
                + (1.0 - min_max_scale(amplitude_values, to_float(item.get("amplitude_4h_pct")))) * 10
                + (to_float(item.get("audit_factor")) or 0.5) * 10
            )
            item["stability_score"] = round(score, 2)
            item["reason"] = self.build_stable_reasons(item)
        analyzed.sort(key=lambda item: item.get("stability_score") or 0.0, reverse=True)
        top_items = analyzed[: (to_int(self.config.get("stable_limit")) or 5)]
        summary = ["稳定刷分分数综合考虑成交额、流动性、持有人、短周期波动、4h 振幅与审计风险。"]
        if top_items:
            summary.insert(0, f"当前最适合稳定刷分的首选是 {top_items[0]['symbol']}，因为流动性与成交额更高，短周期波动更可控。")
        return {"analyzed_count": len(analyzed), "recommendations": top_items, "summary": summary}

    def compute_open_interest_change(self, history: List[Dict[str, Any]]) -> Optional[float]:
        if len(history) < 2:
            return None
        first_value = to_float(history[0].get("sumOpenInterest"))
        last_value = to_float(history[-1].get("sumOpenInterest"))
        if first_value is None or last_value is None or first_value == 0:
            return None
        return (last_value / first_value - 1.0) * 100.0

    def build_futures_alerts(self, alpha_tokens: List[Dict[str, Any]]) -> Dict[str, Any]:
        futures_info = self.safe_call("futures_exchange_info", self.client.get_futures_exchange_info, fallback={})
        futures_tickers = self.safe_call("futures_ticker_24hr", self.client.get_futures_tickers, fallback=[])
        premium_index = self.safe_call("futures_premium_index", self.client.get_futures_premium_index, fallback=[])
        futures_symbols = {item.get("symbol") for item in futures_info.get("symbols") or [] if item.get("status") == "TRADING" and str(item.get("symbol") or "").endswith("USDT")}
        ticker_map = {item.get("symbol"): item for item in futures_tickers}
        premium_map = {item.get("symbol"): item for item in premium_index if item.get("symbol")}
        candidates: List[Dict[str, Any]] = []
        for token in alpha_tokens:
            alpha_symbol = token.get("symbol")
            futures_symbol = f"{alpha_symbol}USDT"
            if futures_symbol not in futures_symbols:
                continue
            ticker = ticker_map.get(futures_symbol) or {}
            premium = premium_map.get(futures_symbol) or {}
            price_change_pct = to_float(ticker.get("priceChangePercent")) or 0.0
            quote_volume = to_float(ticker.get("quoteVolume")) or 0.0
            funding_bps = (to_float(premium.get("lastFundingRate")) or 0.0) * 10000.0
            base_score = abs(price_change_pct) * 0.8 + math.log10(max(quote_volume, 1.0)) * 2.2 + abs(funding_bps) * 0.9
            candidates.append({"alpha_symbol": alpha_symbol, "futures_symbol": futures_symbol, "price_change_percent_24h": price_change_pct, "quote_volume_24h": quote_volume, "funding_bps": funding_bps, "base_score": base_score})
        candidates.sort(key=lambda item: item["base_score"], reverse=True)
        probe_limit = to_int(self.config.get("futures_probe_limit")) or 12
        thresholds = self.config.get("futures_thresholds") or {}
        min_abs_price_change_pct = to_float(thresholds.get("min_abs_price_change_pct")) or 0.0
        min_quote_volume = to_float(thresholds.get("min_quote_volume")) or 0.0
        min_abs_oi_change_pct = to_float(thresholds.get("min_abs_oi_change_pct")) or 0.0
        min_abs_funding_bps = to_float(thresholds.get("min_abs_funding_bps")) or 0.0
        enriched: List[Dict[str, Any]] = []
        for item in candidates[:probe_limit]:
            open_interest_hist = self.safe_call(f"open_interest_hist:{item['futures_symbol']}", self.client.get_open_interest_hist, item["futures_symbol"], fallback=[])
            oi_change_5m_pct = self.compute_open_interest_change(open_interest_hist)
            alert_score = item["base_score"] + abs(oi_change_5m_pct or 0.0) * 1.2
            should_notify = item["quote_volume_24h"] >= min_quote_volume and (abs(item["price_change_percent_24h"]) >= min_abs_price_change_pct or abs(item["funding_bps"]) >= min_abs_funding_bps or abs(oi_change_5m_pct or 0.0) >= min_abs_oi_change_pct)
            reasons = [f"24h 涨跌 {item['price_change_percent_24h']:.2f}%", f"24h 成交额 {item['quote_volume_24h']:,.0f}", f"资金费率 {item['funding_bps']:.2f} bps"]
            if oi_change_5m_pct is not None:
                reasons.append(f"5m 持仓变化 {oi_change_5m_pct:.2f}%")
            enriched.append({**item, "open_interest_change_5m_pct": oi_change_5m_pct, "alert_score": round(alert_score, 2), "should_notify": should_notify, "reasons": reasons})
        enriched.sort(key=lambda item: item["alert_score"], reverse=True)
        return {"matched_contract_count": len(candidates), "alerts": enriched[: (to_int(self.config.get('futures_alert_limit')) or 8)]}

    def build_daily_brief(self, alpha_tokens: List[Dict[str, Any]]) -> Dict[str, Any]:
        recent_listing_hours = to_int(self.config.get("recent_listing_hours")) or 72
        cutoff = datetime.now(timezone.utc) - timedelta(hours=recent_listing_hours)
        recent_alpha_listings: List[Dict[str, Any]] = []
        for token in alpha_tokens:
            listing_time_ms = to_int(token.get("listingTime"))
            if listing_time_ms is None:
                continue
            listing_dt = datetime.fromtimestamp(listing_time_ms / 1000, tz=timezone.utc)
            if listing_dt < cutoff:
                continue
            recent_alpha_listings.append({"symbol": token.get("symbol"), "name": token.get("name"), "mul_point": to_int(token.get("mulPoint")), "listing_time": listing_dt.isoformat(), "volume24h": to_float(token.get("volume24h")), "percent_change_24h": to_float(token.get("percentChange24h"))})
        recent_alpha_listings.sort(key=lambda item: item["listing_time"], reverse=True)
        catalogs = self.safe_call("cms_article_list", self.client.get_announcement_catalogs, fallback=[])
        catalog_map = {to_int(catalog.get("catalogId")): catalog for catalog in catalogs}
        official_updates: List[Dict[str, Any]] = []
        limit = to_int(self.config.get("announcement_limit_per_catalog")) or 3
        for catalog_id in self.config.get("announcement_catalog_ids") or []:
            catalog = catalog_map.get(to_int(catalog_id))
            if not catalog:
                continue
            articles: List[Dict[str, Any]] = []
            for article in (catalog.get("articles") or [])[:limit]:
                code = str(article.get("code") or "")
                detail = self.safe_call(f"cms_article_detail:{code}", self.client.get_announcement_detail, code, fallback={})
                publish_time = ts_to_iso(detail.get("publishDate") or article.get("releaseDate"))
                articles.append({
                    "title": article.get("title"),
                    "code": code,
                    "publish_time": publish_time,
                    "support_url": f"https://www.binance.com/en/support/announcement/detail/{code}",
                    "api_url": f"{CMS_ARTICLE_DETAIL_URL}?articleCode={code}",
                    "summary": body_json_to_summary(detail.get("body")),
                })
            official_updates.append({"catalog_id": to_int(catalog.get("catalogId")), "catalog_name": catalog.get("catalogName"), "articles": articles})
        summary: List[str] = []
        if recent_alpha_listings:
            four_x_count = sum(1 for item in recent_alpha_listings if item.get("mul_point") == 4)
            summary.append(f"过去 {recent_listing_hours} 小时新增 Alpha 代币 {len(recent_alpha_listings)} 个，其中四倍分 {four_x_count} 个。")
        if official_updates:
            newest = safe_first(official_updates[0].get("articles") or [])
            if newest:
                summary.append(f"官方最新上新关注：{newest['title']}")
            for catalog in official_updates[1:]:
                first_article = safe_first(catalog.get("articles") or [])
                if first_article:
                    summary.append(f"{catalog['catalog_name']}：{first_article['title']}")
        return {"recent_alpha_listings": recent_alpha_listings[:8], "official_updates": official_updates, "summary": summary}

def render_markdown(report: Dict[str, Any]) -> str:
    lines: List[str] = []
    lines.extend([
        "# 币安 Alpha 助手日报",
        "",
        f"- 生成时间：{report['generated_at']}",
        f"- 四倍分代币数：{report['quadruple_points']['token_count']}",
        f"- 四倍分 24h 总成交额：{report['quadruple_points']['total_volume_24h']:.2f}",
        f"- 估算参与人数：{(report['quadruple_points']['estimated_participants'] or 0):.0f}（按 {report['assumptions']['participant_volume_standard']} / 人）",
        "",
        "## 四倍分代币",
        "",
    ])
    for item in report["quadruple_points"]["tokens"]:
        lines.append(f"- {item['symbol']} | 成交额 {item['volume24h']:.2f} | 涨跌 {item['percent_change_24h'] or 0:.2f}% | 振幅 {item['amplitude_24h_pct'] or 0:.2f}% | 估算人数 {(item['estimated_participants'] or 0):.0f}")
    lines.extend(["", "## 稳定刷分推荐", ""])
    for item in report["stable_candidates"]["recommendations"]:
        lines.append(f"- {item['symbol']} | 分数 {item['stability_score']:.2f} | 波动 {item.get('realized_volatility_pct') or 0:.2f}% | 4h 振幅 {item.get('amplitude_4h_pct') or 0:.2f}% | 审计 {item.get('audit_risk') or '-'}")
        for reason in item.get("reason") or []:
            lines.append(f"  - {reason}")
    lines.extend(["", "## Alpha 合约异动", "", f"- 可映射 U 本位合约数：{report['futures_alerts']['matched_contract_count']}"])
    for item in report["futures_alerts"]["alerts"]:
        notify_text = "建议通知" if item.get("should_notify") else "继续观察"
        lines.append(f"- {item['alpha_symbol']} / {item['futures_symbol']} | 24h 涨跌 {item['price_change_percent_24h']:.2f}% | 资金费率 {item['funding_bps']:.2f} bps | 5m 持仓变化 {(item.get('open_interest_change_5m_pct') or 0):.2f}% | {notify_text}")
    lines.extend(["", "## Alpha 日报", ""])
    for summary in report["daily_brief"]["summary"]:
        lines.append(f"- {summary}")
    lines.extend(["", "### 最近 Alpha 上线", ""])
    for item in report["daily_brief"]["recent_alpha_listings"]:
        lines.append(f"- {item['symbol']} | {item['mul_point']}x | 上线 {item['listing_time']} | 24h 成交额 {item['volume24h'] or 0:.2f}")
    for catalog in report["daily_brief"]["official_updates"]:
        lines.extend(["", f"### {catalog['catalog_name']}", ""])
        for article in catalog.get("articles") or []:
            lines.append(f"- [{article['title']}]({article['support_url']})")
            if article.get("summary"):
                lines.append(f"  - {article['summary']}")
    if report["warnings"]:
        lines.extend(["", "## Warnings", ""])
        for warning in report["warnings"]:
            lines.append(f"- {warning}")
    lines.append("")
    return "\n".join(lines)


def render_html(report: Dict[str, Any], template_path: Path) -> str:
    return template_path.read_text(encoding="utf-8").replace("__REPORT_JSON__", json.dumps(report, ensure_ascii=False))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate a Binance Alpha report.")
    parser.add_argument("--config", default="config.example.json", help="Path to config JSON file")
    parser.add_argument("--json-output", default="output/latest_report.json", help="JSON output path")
    parser.add_argument("--markdown-output", default="output/latest_report.md", help="Markdown output path")
    parser.add_argument("--html-output", default="output/latest_report.html", help="HTML output path")
    return parser.parse_args()


def main() -> int:
    ensure_utf8_stdout()
    args = parse_args()
    base_dir = Path(__file__).resolve().parent.parent
    config_path = Path(args.config)
    if not config_path.is_absolute():
        config_path = (base_dir / config_path).resolve()
    config = merge_dicts(DEFAULT_CONFIG, load_json(config_path, {})) if config_path.exists() else DEFAULT_CONFIG
    builder = AlphaAssistantBuilder(config)
    report = builder.build()
    json_output = Path(args.json_output)
    markdown_output = Path(args.markdown_output)
    html_output = Path(args.html_output)
    if not json_output.is_absolute():
        json_output = (base_dir / json_output).resolve()
    if not markdown_output.is_absolute():
        markdown_output = (base_dir / markdown_output).resolve()
    if not html_output.is_absolute():
        html_output = (base_dir / html_output).resolve()
    save_json(json_output, report)
    save_text(markdown_output, render_markdown(report))
    save_text(html_output, render_html(report, base_dir / "assets" / "report_template.html"))
    print(f"JSON  : {json_output}")
    print(f"MD    : {markdown_output}")
    print(f"HTML  : {html_output}")
    print(f"Summary: 四倍分 {report['quadruple_points']['token_count']} 个，估算参与人数 {(report['quadruple_points']['estimated_participants'] or 0):.0f}，合约候选 {len(report['futures_alerts']['alerts'])} 个。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
