# 麦省 · 券+积分统一省钱助手  `mcd-frugal`

> 麦当劳程序员节创意开发大赛参赛作品（2026 · 1024）
> **一句话：吃麦当劳时，它告诉你「该掏钱还是该花积分」，哪个更划算。**

![mcd-frugal](https://img.shields.io/badge/麦当劳-MCP%20Skill-ffc72c) ![python](https://img.shields.io/badge/Python-3.10%2B-3776ab) ![zero-dep](https://img.shields.io/badge/零依赖-标准库-2ea44f)

---

## 🤔 为什么需要它

所有人都帮你「找最便宜的券」，但没人回答真正的问题：

> **同一个麦辣鸡腿堡——用现金+券买，还是用积分换，哪个更省？**

麦当劳的**优惠券**和**积分兑换**是两套平行的经济系统（`calculate-price` 根本不接受积分参数），所以绝大多数省钱工具默认把你的积分当废纸。麦省把两条路放在同一张桌上对比，再顺手帮你**审计积分**（哪些快过期、哪些是「纸面富贵」虚标）。

## ✨ 功能

- 🔁 **券 vs 积分 统一决策**：对任意目标餐品，同时算出「现金+最优券」与「积分兑换」两条路的成本，选出更省的一条。
- 🧾 **积分审计**：标出即将过期的积分（提醒你优先用掉）、揪出「积分现金价值 > 官方参考价」的虚标兑换。
- 🧮 **确定性计算**：价格与积分一律由代码 + 官方接口回填，**绝不靠模型心算**（比赛最佳实践）。
- 🔌 **真实 MCP / 离线双模**：配 `MCD_MCP_TOKEN` 走真实麦当劳 MCP；没 Token 也能用内置样本数据跑完整决策（评审零配置可验证）。
- 🛡️ **安全合规**：默认只读 + 计价，下单需用户显式确认，不直接动你的账户。

## 🚀 快速开始

```bash
# 1) 克隆
git clone https://github.com/<你的用户名>/mcd-frugal.git
cd mcd-frugal

# 2) 没 Token？直接看效果（离线演示，无需任何配置）
python3 src/run.py

# 3) 有 Token？走真实麦当劳 MCP（Token 在 https://open.mcd.cn 免费申请）
export MCD_MCP_TOKEN="你的麦当劳MCP Token"
python3 src/run.py 麦辣鸡腿堡

# 4) 真实数据总览（营养密度 + 积分商城审计，只读、不下单）
python3 src/live.py
```

自测（不依赖网络）：

```bash
python3 tests/selftest.py
```

> 真实数据实测示例（`src/live.py`）：积分商城里「21.9元巨无霸可乐组合 = 800 积分（等价¥8.00）」、
> 「28.9元板烧四件套 = 800 积分」等，用积分换比现金买便宜一大截——正是「该掏钱还是花积分」的真实答案。

## 🧩 工作原理

```
门店菜单(query-meals) ─┐
门店券(query-store-coupons) ─┼─▶ 现金路径：calculate-price（券后现金价）
                        │
积分商城(mall-points-products) ─┼─▶ 积分路径：积分成本 × 积分现金价值
账户积分(query-my-account) ─┘
                        │
                        ▼
            统一决策层(FrugalOptimizer)：选更省 + 积分审计
```

核心只做一件事：**数据走 MCP，算数走代码，解释走模型**。优化逻辑见 `src/optimizer.py`（纯函数、可离线测试）。

## 📁 项目结构

```
mcd-frugal/
├── src/
│   ├── mcp_client.py     # 零依赖 streamable-HTTP MCP 客户端
│   ├── mcp_fetch.py      # MCP 原始返回 → 归一化结构（处理分/元单位）
│   ├── optimizer.py      # 券+积分统一决策 + 积分审计（核心纯逻辑）
│   ├── demo.py           # 离线演示（内置样本数据）
│   ├── live.py           # 真实数据总览（营养密度 + 积分商城审计，只读）
│   └── run.py            # CLI：有 Token 走真实 MCP，无 Token 降级演示
├── sample_data/          # 模拟麦当劳 MCP 返回的样本（离线用）
├── tests/selftest.py     # 离线自测
├── SKILL.md              # WorkBuddy Skill 定义
├── MCP_INTEGRATION.md    # 麦当劳 MCP 工具集成说明
├── CONTEST_DECLARATION.md# 参赛声明（官方原文）
├── workbuddy.md          # WorkBuddy 专项奖开发记录
└── mcp-config.example.json
```

## 📜 参赛文件

本仓库已包含活动要求的全部文件：`README.md` / `CONTEST_DECLARATION.md` / `MCP_INTEGRATION.md` / `mcp-config.example.json` / `workbuddy.md`（专项奖）。

## 📄 许可

MIT —— 详见 [LICENSE](LICENSE)。

---

*非麦当劳官方产品，由参赛者基于官方 MCP 能力独立开发。餐品、价格、积分以麦当劳官方实时结果为准。*
