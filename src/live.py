#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
麦省 · 真实数据演示（live mode）
直接调用麦当劳官方 MCP（https://mcp.mcd.cn）拉取真实数据并跑分析。

用法：
    export MCD_MCP_TOKEN="你的麦当劳开放平台Token"
    python3 src/live.py

说明：
  - 仅读取真实营养表 / 积分账户 / 积分商城，不做任何下单操作（安全合规）。
  - 营养数据来自 list-nutrition-foods，积分与商城来自 query-my-account / mall-points-products。
  - 门店相关的「现金+券算价」为可选项（需门店 code），失败会自动跳过，不影响核心分析。
"""

import os
import sys

sys.path.insert(0, os.path.dirname(__file__))

from mcp_client import McdMcpClient
from mcp_fetch import (fetch_nutrition, fetch_account, fetch_mall_products,
                       fetch_meals, fetch_coupons, fetch_calc_price)
from optimizer import FrugalOptimizer


def fmt_yuan(v):
    return "¥%.2f" % v if v is not None else "-"


def nutrition_density_analysis(nutrition):
    """营养密度分析：每 100kcal 的蛋白质含量（高蛋白低密度）+ 钠预警。"""
    rows = []
    for n in nutrition:
        kcal = n.get("energyKcal")
        protein = n.get("protein")
        sodium = n.get("sodium")
        if kcal and protein is not None and kcal > 0:
            rows.append({
                "name": n.get("productName"),
                "kcal": kcal,
                "protein": protein,
                "sodium": sodium,
                "protein_per_100kcal": round(protein / (kcal / 100.0), 1),
            })
    rows.sort(key=lambda r: r["protein_per_100kcal"], reverse=True)
    print("\n🍗 营养密度 TOP8（每 100kcal 蛋白质最高 = 吃了不胖还顶饱）:")
    for r in rows[:8]:
        print("   %-14s %5.0fkcal  蛋白%4.1fg  → %5.1fg/100kcal" %
              (r["name"], r["kcal"], r["protein"], r["protein_per_100kcal"]))

    # 钠预警（绝对值高）
    high_na = [r for r in rows if r["sodium"] is not None and r["sodium"] >= 700]
    high_na.sort(key=lambda r: r["sodium"], reverse=True)
    if high_na:
        print("\n⚠️  高钠预警 TOP5（钠≥700mg，控血压人群注意）:")
        for r in high_na[:5]:
            print("   %-14s 钠 %5.0fmg" % (r["name"], r["sodium"]))


def _parse_embedded_price(name):
    """从商品名里解析嵌入的「X元」现金对标价（如 '21.9元巨无霸可乐组合'）。"""
    import re
    m = re.search(r"(\d+(?:\.\d+)?)\s*元", name or "")
    return float(m.group(1)) if m else None


def points_audit(account, mall):
    """积分审计：账户积分 + 商城商品性价比 + 过期提醒。"""
    avail = account.get("available_points", 0)
    print("\n💰 积分账户:")
    print("   可用积分: %s %s" % (avail, account.get("currency") or ""))
    print("   累计积分: %s" % account.get("accumulative_points", 0))
    if account.get("expiring_points"):
        print("   ⏰ 本月将过期积分: %s（记得本月花掉）" % account["expiring_points"])

    opt = FrugalOptimizer()
    # 用商品名里的嵌入价作为现金对标（mall 接口未直接给现金价）
    for p in mall:
        if p.get("cash_value") in (None, "0", 0, ""):
            p["cash_value"] = _parse_embedded_price(p.get("name"))
    paid = [p for p in mall if p.get("points_cost") not in (None, "0", 0, "")]
    paid.sort(key=lambda p: int(p["points_cost"] or 0), reverse=True)
    print("\n🛒 积分商城审计（付费商品 %d 件，按积分成本排序 TOP10）:" % len(paid))
    for p in paid[:10]:
        cost = int(p["points_cost"] or 0)
        equiv = opt.points_to_yuan(cost)
        ref = p.get("cash_value")
        tag = ""
        if ref is not None:
            if equiv > ref:
                tag = "  ❌积分比现金贵"
            elif equiv <= ref * 0.6:
                tag = "  ✅积分超划算"
            else:
                tag = "  ◐积分略划算"
        print("   %-26s 积分%-5s 等价¥%6.2f  现金对标¥%s%s" %
              (p["name"][:26], cost, equiv, ("%.2f" % ref) if ref else "无", tag))
    if avail:
        can = [p for p in paid if int(p["points_cost"] or 0) <= avail]
        print("\n   当前可用积分 %d 可直接兑换其中: %d 件" % (avail, len(can)))
    else:
        print("\n   （当前账号可用积分为 0，先消费攒积分再来对比『该掏钱还是花积分』）")


def optional_cash_path(client):
    """可选的现金+券算价（需门店，失败自动跳过）。"""
    try:
        near = client.call_tool("query-nearby-stores",
                                {"latitude": 39.9042, "longitude": 116.4074})
        data = client.extract_payload(near) or {}
        arr = data.get("data", data.get("list", []))
        store = arr[0] if isinstance(arr, list) and arr else None
        if not store:
            print("\n（跳过现金算价：未获取到附近门店）")
            return
        store_code = store.get("storeCode") or store.get("code")
        meals = fetch_meals(client, store_code)
        if not meals:
            print("\n（跳过现金算价：该门店无菜单数据）")
            return
        target = meals[0]
        coupons = fetch_coupons(client, store_code)
        payable, unit = fetch_calc_price(client, store_code,
                                         [{"code": target["code"], "qty": 1}])
        print("\n💵 现金路径抽样（门店 %s）:" % store_code)
        print("   餐品: %s 菜单价 %s" % (target["name"], fmt_yuan(target["price"])))
        print("   calculate-price 应付: %s（单位:%s）" % (payable, unit))
        if coupons:
            print("   可用门店券: %d 张" % len(coupons))
    except Exception as e:  # noqa: BLE001
        print("\n（跳过现金算价：%s）" % e)


def main():
    token = os.environ.get("MCD_MCP_TOKEN")
    if not token:
        print("未设置 MCD_MCP_TOKEN 环境变量，无法连接真实 MCP。")
        print("请前往 https://open.mcd.cn 获取 Token 后：export MCD_MCP_TOKEN=...")
        sys.exit(1)

    print("=" * 56)
    print("麦省 · 真实数据演示（live mode）")
    print("=" * 56)
    client = McdMcpClient(token)
    client.initialize()
    print("✅ 已连接麦当劳 MCP，工具数: %d" % len(client.list_tools()))

    nutrition = fetch_nutrition(client)
    print("\n📊 已拉取真实营养数据: %d 条单品" % len(nutrition))
    nutrition_density_analysis(nutrition)

    account = fetch_account(client)
    mall = fetch_mall_products(client)
    points_audit(account, mall)

    optional_cash_path(client)

    print("\n" + "=" * 56)
    print("演示结束 · 本脚本只读、不下单、不泄露 Token")
    print("=" * 56)


if __name__ == "__main__":
    main()
