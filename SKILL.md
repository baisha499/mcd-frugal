---
name: mcd-frugal
description: 麦当劳「券 vs 积分」统一省钱决策助手。当用户想用麦当劳官方 MCP 比较「现金+券」与「积分兑换」哪条路更划算、或想审计自己的积分（过期/虚标）时使用。适用于点餐省钱、积分规划、避免积分浪费等场景。
---

# 麦省 · 券+积分统一省钱助手

## 定位

用户吃麦当劳时，本 Skill 回答一个被忽略的问题：**同一个餐品，用现金+券买，还是用积分换，哪个更省？** 同时审计用户的积分（即将过期、虚标兑换）。

## 何时使用

- 用户问「这个用券还是用积分划算」「帮我算算怎么买最省」
- 用户想规划积分、避免积分过期或踩虚标坑
- 用户要做麦当劳点餐的省钱/积分决策

## 工作流

1. **确认环境**：读取 `MCD_MCP_TOKEN`；若无 Token，用 `src/demo.py` 的内置样本数据做离线演示。
2. **取数（走 MCP）**：`query-meals` 取目标餐品现金价 → `query-store-coupons` + `calculate-price` 得现金券后价 → `mall-points-products` 取积分成本 → `query-my-account` 取积分余额/过期。
3. **决策（走代码）**：调用 `src/optimizer.py` 的 `FrugalOptimizer.compare()` 选更省路径；`audit_points()` 做积分审计。金额/积分一律代码计算，禁止模型心算。
4. **解释（走模型）**：用对比表向用户说明推荐路径与节省金额，并提示积分过期/虚标风险。
5. **安全闸**：默认只读 + 计价；任何下单（`create-order`）必须等用户显式确认，且只产出待支付链接，支付由用户完成。

## 工具依赖（麦当劳 MCP）

`query-meals` / `query-store-coupons` / `calculate-price` / `mall-points-products` / `query-my-account`

## 合规红线

- 不硬编码任何真实 Token；配置仅用 `${MCD_MCP_TOKEN}` 占位符。
- 不评价、不诱导过度消费；输出仅供参考。
- 不下单、不领券、不动账户，除非用户明确确认。
