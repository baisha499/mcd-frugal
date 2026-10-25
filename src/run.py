#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
麦省 CLI：有 Token 走真实 MCP，无 Token 自动降级到离线演示。

用法：
  python run.py                # 无 Token → 离线演示
  python run.py 麦辣鸡腿堡      # 有 Token → 对比该餐品的券/积分路径
  MCD_STORE_CODE=xxxx python run.py 巨无霸
"""

import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

from optimizer import FrugalOptimizer
from demo import run_demo
from mcp_client import McdMcpClient, McdMcpError
from mcp_fetch import (fetch_meals, fetch_coupons, fetch_calc_price,
                       fetch_mall_products, fetch_account)


def main():
    token = os.environ.get("MCD_MCP_TOKEN", "")
    if not token:
        print("⚠️  未检测到 MCD_MCP_TOKEN，自动进入离线演示模式（使用内置样本数据）。")
        print("    申请 Token：https://open.mcd.cn   配置后重跑即可走真实 MCP。\n")
        run_demo()
        return

    try:
        client = McdMcpClient(token)
        client.initialize()
        store = os.environ.get("MCD_STORE_CODE", "")
        meals = fetch_meals(client, store)
        coupons = fetch_coupons(client, store)
        mall = fetch_mall_products(client)
        account = fetch_account(client)
        opt = FrugalOptimizer()

        target = sys.argv[1] if len(sys.argv) > 1 else None
        if not target:
            print("用法: python run.py <餐品名>  例如 python run.py 麦辣鸡腿堡")
            return
        payable, unit = fetch_calc_price(client, store, [target])
        res = opt.compare(target, meals, coupons, payable, mall,
                          account["available_points"])
        import json
        print(json.dumps(res, ensure_ascii=False, indent=2))
    except McdMcpError as e:
        print("MCP 错误:", e)


if __name__ == "__main__":
    main()
