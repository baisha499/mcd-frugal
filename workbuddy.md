# WorkBuddy 专项奖励开发记录

本作品由腾讯 WorkBuddy 智能体（Agent）辅助完成开发，符合「真实使用 WorkBuddy 智能体」的专项奖励要求。

## 开发过程（WorkBuddy 上下文）

1. **赛道侦察**：通过 WorkBuddy 联网调研了活动官方实时排行榜（99+ 上榜项目），按赛道归类分析拥挤度，确定「省钱/券」赛道已高度内卷（头部 1365/1322/1004 star），而「优惠券 + 积分兑换」的统一决策是空白切口。
2. **方案确定**：明确作品定位为「券 vs 积分 统一省钱决策 + 积分审计」，遵循「数据走 MCP、算数走代码、解释走模型」最佳实践。
3. **代码实现**：在 WorkBuddy 中完成零依赖 MCP 客户端（`mcp_client.py`）、归一化取数层（`mcp_fetch.py`）、纯逻辑优化器（`optimizer.py`）、离线演示与 CLI（`demo.py` / `run.py`）。
4. **可验证性**：内置 `sample_data/` 样本与 `tests/selftest.py` 离线自测，无 Token 也能跑完整决策循环，评审零配置可验证。
5. **合规交付**：产出全套参赛文件（README / CONTEST_DECLARATION / MCP_INTEGRATION / mcp-config.example / 本文件）。

## 使用的 WorkBuddy 能力

- 联网检索（WebSearch / WebFetch）获取官方排行榜与 MCP 工具说明
- 代码生成与多轮迭代（Python、零第三方依赖）
- 文档生成（参赛声明、集成说明、Skill 定义）

## 与活动的联动

- 作品即一个可直接加载到 WorkBuddy 的 Skill（`SKILL.md`），用户在 WorkBuddy 中一句话即可调用。
- 真实接入麦当劳官方 MCP，符合「真实使用麦当劳 MCP 能力」要求。
