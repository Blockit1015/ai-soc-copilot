from fastapi.testclient import TestClient


def test_health_returns_fixed_contract() -> None:
    from app.main import app          #导入应用， 从app/main.py 里把FastAPI程序拿过来。如果这个文件不存在，测试第一步就会报错。

    client = TestClient(app)      #创建一个模拟的浏览器
    response = client.get("/health")   #模拟发送GET请求到 /health

    assert response.status_code == 200    #检查状态码是不是 200 (成功)

    assert response.json() == {           #断言（检查）返回的 JSON 内容是否完全符合规定————契约
        "status": "ok",
        "service": "ai-soc-copilot",
        "version": "0.1.0",
        "environment": "local-training",
    }
