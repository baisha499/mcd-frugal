#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
麦当劳官方 MCP 服务的轻量 streamable-HTTP 客户端（零第三方依赖）。

协议要点（基于 MCP streamable HTTP 规范 + 麦当劳 open.mcd.cn 实测）：
  - 端点：https://mcp.mcd.cn
  - 鉴权：Authorization: Bearer <MCD_MCP_TOKEN>
  - 请求体：JSON-RPC 2.0
  - initialize 响应头携带 Mcp-Session-Id，后续请求需回带
  - 响应可能是 application/json 或 text/event-stream(SSE)，本客户端两者都解析

设计原则（与比赛最佳实践一致）：
  - 数据检索全部走 MCP（菜单 / 券 / 积分商城 / 账户）
  - 任何金额与积分计算都不在模型里“心算”，一律由代码 + 官方接口回填
"""

import json
import time
import urllib.request
import urllib.error

DEFAULT_ENDPOINT = "https://mcp.mcd.cn"
PROTOCOL_VERSION = "2024-11-05"
CLIENT_NAME = "mcd-frugal"
CLIENT_VERSION = "1.0.0"


class McdMcpError(RuntimeError):
    """MCP 调用层面的错误。"""


class McdMcpClient:
    def __init__(self, token, endpoint=DEFAULT_ENDPOINT, timeout=30, max_retries=2):
        if not token:
            raise McdMcpError("缺少 MCP Token，请设置环境变量 MCD_MCP_TOKEN 或在配置中提供。")
        self.token = token
        self.endpoint = endpoint.rstrip("/")
        self.timeout = timeout
        self.max_retries = max_retries
        self.session_id = None
        self._id = 0
        self._initialized = False

    def _next_id(self):
        self._id += 1
        return self._id

    @staticmethod
    def _parse_body(body, content_type):
        body = (body or "").strip()
        if not body:
            return None
        ctype = (content_type or "").lower()
        if ("text/event-stream" in ctype) or body.startswith("event:") \
                or body.startswith("data:") or "\ndata:" in body:
            last = None
            for line in body.splitlines():
                line = line.strip()
                if line.startswith("data:"):
                    chunk = line[len("data:"):].strip()
                    if chunk:
                        try:
                            last = json.loads(chunk)
                        except json.JSONDecodeError:
                            continue
            return last
        try:
            return json.loads(body)
        except json.JSONDecodeError:
            return {"raw": body}

    def _headers(self):
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json, text/event-stream",
            "Authorization": "Bearer %s" % self.token,
        }
        if self.session_id:
            headers["Mcp-Session-Id"] = self.session_id
        return headers

    def _request(self, payload, is_notification=False):
        data = json.dumps(payload).encode("utf-8")
        last_err = None
        for attempt in range(self.max_retries + 1):
            try:
                req = urllib.request.Request(
                    self.endpoint, data=data, headers=self._headers(), method="POST"
                )
                with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                    sid = resp.headers.get("Mcp-Session-Id")
                    if sid:
                        self.session_id = sid
                    body = resp.read().decode("utf-8", "replace")
                    if is_notification:
                        return {"status": resp.status}
                    return self._parse_body(body, resp.headers.get("Content-Type"))
            except urllib.error.HTTPError as e:
                detail = e.read().decode("utf-8", "replace")
                last_err = McdMcpError("MCP HTTP %s: %s" % (e.code, detail))
                if e.code in (401, 403):
                    raise last_err
            except Exception as e:  # noqa: BLE001
                last_err = McdMcpError("MCP 请求失败: %s" % e)
            if attempt < self.max_retries:
                time.sleep(0.5 * (attempt + 1))
        raise last_err or McdMcpError("MCP 请求失败（未知原因）")

    def initialize(self):
        if self._initialized:
            return True
        init_payload = {
            "jsonrpc": "2.0",
            "id": self._next_id(),
            "method": "initialize",
            "params": {
                "protocolVersion": PROTOCOL_VERSION,
                "capabilities": {},
                "clientInfo": {"name": CLIENT_NAME, "version": CLIENT_VERSION},
            },
        }
        self._request(init_payload)
        self._request(
            {"jsonrpc": "2.0", "method": "notifications/initialized", "params": {}},
            is_notification=True,
        )
        self._initialized = True
        return True

    def list_tools(self):
        self.initialize()
        resp = self._request(
            {"jsonrpc": "2.0", "id": self._next_id(), "method": "tools/list", "params": {}}
        )
        if isinstance(resp, dict) and "result" in resp:
            return resp["result"].get("tools", [])
        return []

    def call_tool(self, name, arguments=None):
        self.initialize()
        resp = self._request(
            {
                "jsonrpc": "2.0",
                "id": self._next_id(),
                "method": "tools/call",
                "params": {"name": name, "arguments": arguments or {}},
            }
        )
        return resp

    @staticmethod
    def extract_text(result):
        if result is None:
            return ""
        if isinstance(result, str):
            return result
        if isinstance(result, dict):
            if "result" in result and isinstance(result["result"], dict):
                return McdMcpClient._join_content(result["result"].get("content", []))
            if "content" in result:
                return McdMcpClient._join_content(result["content"])
            return json.dumps(result, ensure_ascii=False)
        return str(result)

    @staticmethod
    def _join_content(content):
        parts = []
        for item in content or []:
            if isinstance(item, dict):
                if item.get("type") == "text":
                    parts.append(item.get("text", ""))
                elif "data" in item:
                    parts.append(json.dumps(item["data"], ensure_ascii=False))
        return "\n".join(p for p in parts if p)

    @staticmethod
    def extract_json(result):
        text = McdMcpClient.extract_text(result)
        if not text:
            return None
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            return None


def from_env(endpoint=DEFAULT_ENDPOINT):
    import os
    token = os.environ.get("MCD_MCP_TOKEN", "")
    if not token:
        raise McdMcpError("未找到环境变量 MCD_MCP_TOKEN，请先前往 open.mcd.cn 获取并导出。")
    return McdMcpClient(token, endpoint=endpoint)
