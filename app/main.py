from fastapi import FastAPI            #引入 FastAPI 框架

# 把D02的“接收告警的接口”（investigations_router）拿过来挂到总控制台上
from app.api.investigations import router as investigations_router  #负责接收告警、生成 ID
# 把D03的“案件查询接口”（investigation_context_router）拿过来挂到总控制台上
from app.api.investigation_context import router as investigation_context_router #负责根据ID查库、返回Case/Evidence绑定信息
from app.api.agent_runs import router as agent_runs_router #把D04的Agent运行接口（agent_runs_router）拿过来挂到总控制台上，负责接收运行请求、调用AgentRuntime、返回运行结果与轨迹

app = FastAPI()  # 创建一个 FastAPI 实例（这是整个应用的入口）
app.include_router(investigations_router) #把D02的“接收告警的接口”（路由）挂到这个引擎上，这样访问此接口时，引擎就知道去哪里找代码了
app.include_router(investigation_context_router)
app.include_router(agent_runs_router)


@app.get("/health")    #这是一个装饰器，定义路由：当有人访问 /health 时，执行下面的函数

def health() -> dict[str, str]:
    return {                             #执行结果是：返回固定的 JSON 数据——契约
        "status": "ok",
        "service": "ai-soc-copilot",
        "version": "0.1.0",
        "environment": "local-training",
    }

# 这是总启动程序，当访问这个系统时，所有的请求都会先经过这个app = FastAPI() 创建出来的“总控制台“
# 为什么所有请求都要经过它？
# 系统是一栋办公大楼，里面有很多个部门（比如D02建的“告警接收部”，D03建的“案件查询部”）
# app = FastAPI()：这行相当于前台
# app.include_router(...)：让前台知道：“如果要接收告警，去找 investigations 部门；（同理后面，如果要查案件，去找context 部门”）
# 当外部请求（比如浏览器或测试代码）访问系统时，它们不知道你的系统里有哪些部门。它们只能找到总入口，也就是 main.py 里的 app
# 流程是这样的：请求进来，先找到 app（总前台），app 看一下请求的地址（比如 /health 或者 /api/v1/investigations/xxx）。
# app把请求派发给对应的部门（函数）去处理。部门处理完，把结果交还给 app，app再把结果返回给外部。
# app = FastAPI() 是所有的部门（路由）与外部通信的媒介。
