#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
把麦当劳 MCP 的原始返回规整成优化器需要的归一化结构。

真实响应特征（基于 open.mcd.cn 实测）：
  - 返回体被「描述性 markdown + ## Original Response + 原始 JSON」包裹，
    统一用 mcp_client.extract_payload 抽取内层 JSON。
  - list-nutrition-foods 的 data 是「自定义文本」而非 JSON：
      [160]{productName,nutritionDescription,energyKj,energyKcal,protein,
            fat,carbohydrate,sodium,calcium}:
        猪柳麦满分,null,1288,308,16,16,24,781,213
    → 需要 parse_nutrition_text 单独解析。
  - query-my-account / mall-points-products 的 data 是标准 JSON。
  - 金额单位：query-meals.currentPrice 多为「元」；calculate-price 多为「分」。

真实字段名以官方 MCP 返回为准，这里做了常见别名的兼容。
"""

import re

from mcp_client import McdMcpClient


def parse_nutrition_text(data_str):
    """解析 list-nutrition-foods 返回的自定义文本表。

    返回：[{productName, energyKcal, protein, fat, carbohydrate, sodium, calcium}, ...]
    数值字段统一转成 float（'null'/空 → None）。
    """
    if not data_str or not isinstance(data_str, str):
        return []
    lines = data_str.splitlines()
    cols = []
    for ln in lines:
        if ln.strip().startswith("["):
            m = re.search(r"\{([^}]*)\}", ln)
            if m:
                cols = [c.strip() for c in m.group(1).split(",")]
            break
    if not cols:
        return []
    numeric = {"energyKj", "energyKcal", "protein", "fat", "carbohydrate",
               "sodium", "calcium"}

    def to_num(v):
        if v is None:
            return None
        v = v.strip()
        if v.lower() in ("null", "", "none"):
            return None
        try:
            return float(v)
        except ValueError:
            return None

    items = []
    for ln in lines:
        s = ln.strip()
        if not s or s.startswith("[") or s.startswith("#") or s.startswith("-"):
            continue
        parts = [p.strip() for p in s.split(",")]
        if len(parts) < len(cols):
            continue
        row = {}
        for i, c in enumerate(cols):
            val = parts[i] if i < len(parts) else None
            row[c] = to_num(val) if c in numeric else val
        items.append(row)
    return items


def fetch_nutrition(client):
    raw = client.call_tool("list-nutrition-foods", {})
    payload = client.extract_payload(raw) or {}
    data = payload.get("data")
    if isinstance(data, str):
        return parse_nutrition_text(data)
    if isinstance(data, list):
        return data
    return []


def fetch_meals(client, store_code=None):
    args = {}
    if store_code:
        args["storeCode"] = store_code
    raw = client.call_tool("query-meals", args)
    data = client.extract_payload(raw) or {}
    meals = []
    for m in data.get("meals", data.get("list", data.get("data", []))):
        meals.append({
            "code": m.get("code") or m.get("mealCode") or m.get("id"),
            "name": m.get("name"),
            "price": m.get("currentPrice", m.get("price")),
            "price_unit": "yuan",
        })
    return meals


def fetch_coupons(client, store_code=None):
    args = {}
    if store_code:
        args["storeCode"] = store_code
    raw = client.call_tool("query-store-coupons", args)
    data = client.extract_payload(raw) or {}
    coupons = []
    for c in data.get("coupons", data.get("list", data.get("data", []))):
        coupons.append({
            "id": c.get("id") or c.get("couponId"),
            "name": c.get("name"),
            "type": c.get("type", "minus"),
            "value": c.get("value", c.get("discount")),
            "scope": c.get("scope", c.get("applicableItems", [])),
        })
    return coupons


def fetch_calc_price(client, store_code, items, coupon_id=None, take_way="eat-in"):
    args = {"storeCode": store_code, "items": items, "takeWay": take_way}
    if coupon_id:
        args["couponId"] = coupon_id
    raw = client.call_tool("calculate-price", args)
    data = client.extract_payload(raw) or {}
    payable = data.get("payable", data.get("payablePrice",
                                          data.get("totalPay", data.get("total"))))
    return payable, "cent"  # calculate-price 金额多为分，交给 optimizer 转元


def fetch_mall_products(client):
    raw = client.call_tool("mall-points-products", {})
    data = client.extract_payload(raw) or {}
    # data 可能是数组，也可能是含 list/data 字段的对象
    arr = data
    if isinstance(data, dict):
        arr = data.get("list", data.get("data", data.get("products", [])))
    products = []
    for p in (arr or []):
        products.append({
            "id": p.get("id") or p.get("spuId"),
            "name": p.get("spuName") or p.get("name"),
            "points_cost": p.get("point") or p.get("pointsCost") or p.get("points"),
            "cash_value": p.get("cashPrice") if p.get("cashPrice") is not None
            else p.get("price"),
        })
    return products


def fetch_account(client):
    raw = client.call_tool("query-my-account", {})
    data = client.extract_payload(raw) or {}
    acct = data.get("data", data)
    if isinstance(acct, dict):
        return {
            "available_points": int(float(acct.get("availablePoint", 0) or 0)),
            "accumulative_points": int(float(acct.get("accumulativePoint", 0) or 0)),
            "expiring_points": int(float(acct.get("currentMouthExpirePoint", 0) or 0)),
            "expiring_date": None,
            "currency": acct.get("currency"),
        }
    return {"available_points": 0, "accumulative_points": 0,
            "expiring_points": 0, "expiring_date": None, "currency": None}
