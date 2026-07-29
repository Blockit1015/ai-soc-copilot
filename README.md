# AI-SOC Copilot

这是 AI-SOC Copilot 的 D01 本地训练工程。当前阶段只建立最小 FastAPI 工程入口，并通过自动化测试验证固定的健康接口契约。

## 当前范围

本次只计划实现：

```http
GET /health
```

固定响应契约：

```json
{
  "status": "ok",
  "service": "ai-soc-copilot",
  "version": "0.1.0",
  "environment": "local-training"
}
```

当前仅完成规则、说明、依赖声明和目录骨架；`/health` 尚未实现，也没有测试通过结果。

## 后续验证命令

实现测试和接口后，使用以下命令进行真实验证：

```powershell
python -m pytest tests/test_health.py -q
python -m pytest -q
python -m uvicorn app.main:app --reload
curl.exe http://127.0.0.1:8000/health
```

## 明确不做

D01 不实现告警、Case、Agent、RAG、真实模型、数据库、鉴权、Docker、部署或生产系统连接。

健康接口即使通过，也只能证明当前最小服务入口能够响应，不能证明完整业务链路、外部依赖、性能、安全性或生产可用性。

