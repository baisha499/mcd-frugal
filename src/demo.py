#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
离线演示：用内置样本数据跑一遍「券 vs 积分」统一优化，无需 Token。
样本数据来自 sample_data/ 目录（模拟麦当劳 MCP 的真实返回结构）。
"""

import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
SAMPLE_DIR = os.path.join(ROOT, "sample_data")
sys.path.insert(0, HERE)

from optimizer import FrugalOptimizer


def _load(name):
    path = os.path.join(SAMPLE_DIR, name)
    if not os.path.exists(path):
        return None
    import json
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def run_demo():
    meals_doc = _load("meals.json") or {"meals": []}
    coupons_doc = _load("coupons.json") or {"coupons": []}
    mall_doc = _load("mall_products.json") or {"products": []}
    account_doc = _load("account.json") or {}

    meals = meals_doc.get("meals", [])
    coupons = coupons_doc.get("coupons", [])
    mall = mall_doc.get("products", [])
    available_points = account_doc.get("availablePoints", 0)
    expiring_points = account_doc.get("expiringPoints", 0)
    expiring_date = account_doc.get("expiringDate")

    opt = FrugalOptimizer(point_value=0.01)

    print("=" * 58)
    print("   麦省 · 券+积分统一省钱助手  —  离线演示（无 Token）")
    print("=" * 58)

    for name in [m["name"] for m in meals]:
        res = opt.compare(name, meals, coupons, None, mall, available_points)
        if not res["ok"]:
            print("\n🍔 %s：%s" % (name, res["reason"]))
            continue
        cash = res["cash"]
        pts = res["points"]
        print("\n🍔 目标：%s" % name)
        print("   现金路径：%.2f 元（券：%s，省 %.2f）" % (
            cash["payable_yuan"], cash["coupon"] or "无", cash["saved_vs_base"]))
        if pts:
            print("   积分路径：%d 积分 ≈ %.2f 元（可兑换：%s）" % (
                pts["points_cost"], pts["cash_equivalent_yuan"],
                "是" if pts["affordable"] else "积分不足(差%d)" % pts["points_short"]))
        print("   👉 推荐：%s   本单省 %.2f 元" % (res["recommend"], res["saving_yuan"]))

    print("\n" + "-" * 58)
    print("   积分审计")
    print("-" * 58)
    audit = opt.audit_points(mall, available_points, expiring_points, expiring_date)
    print("   可用积分：%d，即将过期：%d（%s）" % (
        audit["available_points"], audit["expiring_points"],
        audit["expiring_date"] or "无"))
    if audit["expiring_warning"]:
        print("   ⚠️ 有积分即将过期，优先用掉！")
    for r in audit["products"]:
        flag = "⚠️虚标" if r["overpriced"] else "✅值"
        ref = ("%.2f" % r["cash_reference_yuan"]) if r["cash_reference_yuan"] is not None else "无"
        print("   %s %s：%d 积分≈%.2f 元（参考价 %s）" % (
            flag, r["name"], r["points_cost"], r["cash_equivalent_yuan"], ref))
    print("\n✅ 演示完成。配置 MCD_MCP_TOKEN 后跑 `python run.py <餐品名>` 走真实数据。")
    return True


if __name__ == "__main__":
    run_demo()
