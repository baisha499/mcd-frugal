#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
离线自测：不依赖网络 / Token，验证优化器核心逻辑与 demo 可运行。
运行：python tests/selftest.py
"""

import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "src"))

from optimizer import FrugalOptimizer
from demo import run_demo

SAMPLE_DIR = os.path.join(ROOT, "sample_data")


def _load(name):
    import json
    with open(os.path.join(SAMPLE_DIR, name), "r", encoding="utf-8") as f:
        return json.load(f)


def main():
    meals = _load("meals.json")["meals"]
    coupons = _load("coupons.json")["coupons"]
    mall = _load("mall_products.json")["products"]
    acct = _load("account.json")
    opt = FrugalOptimizer(point_value=0.01)

    fails = 0

    # 1) 麦辣鸡腿堡：积分路径(15元) 应优于 现金券后(16元)
    r = opt.compare("麦辣鸡腿堡", meals, coupons, None, mall, acct["availablePoints"])
    assert r["ok"], r
    assert r["cash"]["payable_yuan"] == 16.0, r["cash"]
    assert r["points"]["points_cost"] == 1500
    assert r["recommend"] == "points", r
    assert r["saving_yuan"] == 1.0, r

    # 2) 巨无霸：现金券后(21元) 优于 积分(22元)
    r = opt.compare("巨无霸", meals, coupons, None, mall, acct["availablePoints"])
    assert r["cash"]["payable_yuan"] == 21.0, r["cash"]
    assert r["recommend"] == "cash", r

    # 3) 积分不足场景：把可用积分设很低时，积分路径不可负担
    r = opt.compare("麦辣鸡腿堡", meals, coupons, None, mall, 100)
    assert r["points"]["affordable"] is False, r
    assert r["recommend"] == "cash", r

    # 4) 积分审计：可口可乐(积分) 800分≈8元 > 参考价6元 → 虚标
    audit = opt.audit_points(mall, acct["availablePoints"], acct["expiringPoints"], acct["expiringDate"])
    assert audit["expiring_warning"] is True
    overpriced = [p for p in audit["products"] if p["overpriced"]]
    assert len(overpriced) == 1 and "可口可乐" in overpriced[0]["name"], audit

    # 5) demo 可运行
    assert run_demo() is True

    print("✅ 全部自测通过（5 组断言）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
