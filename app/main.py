from fastapi import FastAPI


app = FastAPI()


@app.get("/health")
def health() -> dict[str, str]:
    return {
        "status": "ok",
        "service": "ai-soc-copilot",
        "version": "0.1.0",
        "environment": "local-training",
    }
