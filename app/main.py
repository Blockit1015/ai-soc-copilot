from fastapi import FastAPI  #引入 FastAPI 框架

from app.api.investigations import router as investigations_router


app = FastAPI()  # 创建一个 FastAPI 实例（这是整个应用的入口）
app.include_router(investigations_router)


@app.get("/health")    #这是一个装饰器，定义路由：当有人访问 /health 时，执行下面的函数

def health() -> dict[str, str]:
    return {                             #返回固定的 JSON 数据——契约
        "status": "ok",
        "service": "ai-soc-copilot",
        "version": "0.1.0",
        "environment": "local-training",
    }
