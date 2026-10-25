# MCP 集成说明（麦当劳官方 MCP Server）

本作品基于麦当劳中国官方 MCP 能力开发，端点与鉴权如下：

- **端点**：`https://mcp.mcd.cn`
- **协议**：Streamable HTTP（JSON-RPC 2.0）
- **鉴权**：`Authorization: Bearer ${MCD_MCP_TOKEN}`（Token 在 https://open.mcd.cn 免费申请）
- **配额**：600 次/分钟

## 实际使用的工具

| 工具 | 用途 | 在作品中的角色 |
|---|---|---|
| `query-meals` | 查询门店在售餐品与价格 | 取目标餐品现金价（注意 `currentPrice` 单位为**元**） |
| `query-store-coupons` | 查询门店可用券 | 现金路径的券选优 |
| `calculate-price` | 带券算价 | 现金路径最终应付金额（注意金额单位为**分**） |
| `mall-points-products` | 积分商城商品列表 | 积分路径的商品与积分成本 |
| `query-my-account` | 查询账户积分 | 积分余额、即将过期积分审计 |

> 说明：积分兑换（`mall-*`）与现金算价（`calculate-price`）是平行系统，`calculate-price` 不接受积分参数，因此作品在**决策层**而非价格调用层做「券 vs 积分」的统一对比——这是本作品与纯优惠券省钱工具的核心差异。

## 调用流程

```
1. initialize → notifications/initialized      （建立会话，处理 Mcp-Session-Id）
2. query-meals            → 目标餐品现金价
3. query-store-coupons    → 候选券
4. calculate-price        → 现金券后价（分→元）
5. mall-points-products   → 同款/等价商品的积分成本
6. query-my-account       → 积分余额 / 即将过期
7. FrugalOptimizer.compare()  → 选更省的一条
8. FrugalOptimizer.audit_points() → 积分过期/虚标审计
```

## 业务价值

- **对用户**：一句话回答「该掏钱还是该花积分」，并把被忽略的积分价值显性化。
- **对赛事**：演示了「优惠券」与「积分兑换」两套经济系统的统一决策范式，扩展了省钱类 Skill 的边界（现有头部作品多只看券）。
- **工程合规**：数据检索全部走 MCP；金额/积分为确定性代码计算，非模型估算；默认只读 + 计价，下单需用户确认。
