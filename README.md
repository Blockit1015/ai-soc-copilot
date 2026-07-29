# AI-SOC Copilot

这是 AI-SOC Copilot 的 D01 本地训练工程。D01 已完成最小 FastAPI 工程入口、`GET /health` 健康接口和固定响应契约测试。

## 当前范围

本次已实现：

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

`GET /health` 已实现，并由 `tests/test_health.py` 检查 HTTP `200` 和完整 JSON 响应契约。

## 安装依赖

```powershell
python -m pip install -r requirements.txt
```

## 启动命令

```powershell
python -m uvicorn app.main:app --reload
```

## 验证命令

```powershell
python -m pytest tests/test_health.py -q
python -m pytest -q
```

服务保持运行时，在另一个终端访问健康接口：

```powershell
curl.exe http://127.0.0.1:8000/health
```

## 明确不做

D01 不实现告警、Case、Agent、RAG、真实模型、数据库、鉴权、Docker、部署或生产系统连接。

健康接口即使通过，也只能证明当前最小服务入口能够响应，不能证明完整业务链路、外部依赖、性能、安全性或生产可用性。
