#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
麦省 · 券+积分统一省钱优化器（纯逻辑层，零依赖、可离线测试）。

核心思想：麦当劳的「优惠券」与「积分兑换」是两套平行经济系统，
calculate-price 不接受积分参数，因此无法在同一笔算价里合并。
本模块做的是「决策对比层」：对任意目标餐品，同时给出
  - 路径A：现金 + 最优券（calculate-price 结果，单位元）
  - 路径B：用积分兑换（mall-* 结果，单位积分）
并基于可配置的「积分现金价值」选出更省的一条，同时审计积分（过期/虚标）。
"""

DEFAULT_POINT_VALUE = 0.01  # 1 积分 ≈ ¥0.01（可在配置中校准）


def _to_yuan(value, unit_hint="yuan"):
    """把金额统一成「元」。query-meals 的 currentPrice 多为元；
    calculate-price 多为分；这里按调用方标注的 unit 处理。"""
    if value is None:
        return None
    if unit_hint == "cent":
        return round(float(value) / 100.0, 2)
    return round(float(value), 2)


class FrugalOptimizer:
    def __init__(self, point_value: float = DEFAULT_POINT_VALUE):
        self.point_value = point_value

    def points_to_yuan(self, points: int) -> float:
        return round(points * self.point_value, 2)

    def cash_path(self, item, best_coupon=None, payable_yuan=None):
        base = _to_yuan(item.get("price"), item.get("price_unit", "yuan"))
        if payable_yuan is not None:
            payable = _to_yuan(payable_yuan, "yuan")
        else:
            payable = base
            if best_coupon:
                payable = self._apply_coupon(base, best_coupon)
        return {
            "base_yuan": base,
            "coupon": best_coupon["name"] if best_coupon else None,
            "payable_yuan": payable,
            "saved_vs_base": round(base - payable, 2),
        }

    @staticmethod
    def _apply_coupon(base, coupon):
        t = coupon.get("type")
        v = float(coupon.get("value", 0))
        if t == "minus":       # 满减/直减：减 v 元
            return max(0.0, round(base - v, 2))
        if t == "percent":     # 折扣：v 表示折扣率（0.9 = 9 折）
            return round(base * v, 2)
        if t == "fixed":       # 一口价
            return round(min(base, v), 2)
        return base

    def points_path(self, mall_product, available_points):
        cost = int(mall_product.get("points_cost", 0))
        cash_equiv = self.points_to_yuan(cost)
        enough = available_points >= cost
        return {
            "product": mall_product.get("name"),
            "points_cost": cost,
            "cash_equivalent_yuan": cash_equiv,
            "affordable": enough,
            "points_short": max(0, cost - available_points),
        }

    def compare(self, item_name, meals, coupons, payable_yuan, mall_products,
                available_points):
        item = self._find(meals, item_name)
        if not item:
            return {"ok": False, "reason": "菜单中未找到 %s" % item_name}
        best_coupon = self._best_coupon(item, coupons)
        cash = self.cash_path(item, best_coupon, payable_yuan)
        mall = self._find(mall_products, item_name)
        result = {
            "ok": True,
            "item": item_name,
            "cash": cash,
            "points": None,
            "recommend": None,
            "saving_yuan": 0.0,
        }
        if mall:
            pts = self.points_path(mall, available_points)
            result["points"] = pts
            if pts["affordable"] and pts["cash_equivalent_yuan"] < cash["payable_yuan"]:
                result["recommend"] = "points"
                result["saving_yuan"] = round(cash["payable_yuan"] - pts["cash_equivalent_yuan"], 2)
            else:
                result["recommend"] = "cash"
                if best_coupon:
                    result["saving_yuan"] = cash["saved_vs_base"]
        else:
            result["recommend"] = "cash"
            if best_coupon:
                result["saving_yuan"] = cash["saved_vs_base"]
        return result

    def audit_points(self, mall_products, available_points, expiring_points=0,
                     expiring_date=None):
        rows = []
        for p in mall_products:
            cost = int(p.get("points_cost", 0))
            ref = p.get("cash_value") if p.get("cash_value") is not None else p.get("cash_reference_yuan")
            ref_yuan = _to_yuan(ref, "yuan") if ref is not None else None
            overpriced = (ref_yuan is not None and self.points_to_yuan(cost) > ref_yuan)
            rows.append({
                "name": p.get("name"),
                "points_cost": cost,
                "cash_equivalent_yuan": self.points_to_yuan(cost),
                "cash_reference_yuan": ref_yuan,
                "overpriced": overpriced,
            })
        return {
            "available_points": available_points,
            "expiring_points": expiring_points,
            "expiring_date": expiring_date,
            "expiring_warning": expiring_points > 0,
            "products": rows,
            "overpriced_count": sum(1 for r in rows if r["overpriced"]),
        }

    @staticmethod
    def _find(items, name):
        if not items:
            return None
        for it in items:
            if it.get("name") == name:
                return it
        for it in items:
            if name and name in (it.get("name") or ""):
                return it
        return None

    def _best_coupon(self, item, coupons):
        best = None
        base = _to_yuan(item.get("price"), item.get("price_unit", "yuan"))
        for c in (coupons or []):
            scope = c.get("scope", [])
            if scope and item.get("code") not in scope and item.get("name") not in scope:
                continue
            pay = self._apply_coupon(base, c)
            if best is None or pay < best[1]:
                best = (c, pay)
        return best[0] if best else None
