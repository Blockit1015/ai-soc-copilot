# AI-SOC Copilot 工程规则

## 当前工程树

只允许维护以下工程文件：

```text
ai-soc-copilot/
├─ AGENTS.md
├─ README.md
├─ requirements.txt
├─ app/
│  ├─ __init__.py
│  └─ main.py
└─ tests/
   └─ test_health.py
```

## 常用命令

启动本地服务：

```powershell
python -m uvicorn app.main:app --reload
```

运行聚焦测试：

```powershell
python -m pytest tests/test_health.py -q
```

运行全部测试：

```powershell
python -m pytest -q
```

## 工作规则

- 每次只完成当前明确要求的任务，不提前扩展范围。
- 先编写测试并确认它因功能尚未实现而失败，再做最小实现。
- 不得为了通过测试而删除、跳过或弱化断言。
- 修改后必须查看完整 Diff，并亲自运行相关测试。
- 测试、接口和 Commit 结果只能记录真实运行结果。
- 不加入凭据、真实企业数据、生产账号或生产连接。
- D01 不实现告警、Case、Agent、RAG、模型、数据库、鉴权、Docker 或部署。

