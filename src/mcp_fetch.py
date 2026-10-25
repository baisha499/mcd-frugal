#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
把麦当劳 MCP 的原始返回规整成优化器需要的归一化结构。

注意单位：query-meals 的 currentPrice 多为「元」；calculate-price 的金额为「分」。
本模块按工具分别标注 unit，统一交给 optimizer 处理。
真实字段名以官方 MCP 返回为准，这里做了常见别名的兼容。
"""

from mcp_client import McdMcpClient


def fetch_meals(client, store_code=None):
    args = {}
    if store_code:
        args["storeCode"] = store_code
    raw = client.call_tool("query-meals", args)
    data = client.extract_json(raw) or {}
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
    # 优先门店券，失败回退到可用券
    args = {}
    if store_code:
        args["storeCode"] = store_code
    raw = client.call_tool("query-store-coupons", args)
    data = client.extract_json(raw) or {}
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
    data = client.extract_json(raw) or {}
    payable = data.get("payable", data.get("payablePrice", data.get("totalPay", data.get("total"))))
    return payable, "cent"  # calculate-price 金额多为分，交给 optimizer 转元


def fetch_mall_products(client):
    raw = client.call_tool("mall-points-products", {})
    data = client.extract_json(raw) or {}
    products = []
    for p in data.get("products", data.get("list", data.get("data", []))):
        products.append({
            "id": p.get("id") or p.get("spuId"),
            "name": p.get("name"),
            "points_cost": p.get("pointsCost", p.get("points")),
            "cash_value": p.get("cashValue", p.get("cashPrice")),
        })
    return products


def fetch_account(client):
    raw = client.call_tool("query-my-account", {})
    data = client.extract_json(raw) or {}
    return {
        "available_points": data.get("availablePoints", data.get("points", 0)),
        "expiring_points": data.get("expiringPoints", 0),
        "expiring_date": data.get("expiringDate"),
    }
