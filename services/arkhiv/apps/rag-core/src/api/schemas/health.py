from pydantic import BaseModel


class HealthResponse(BaseModel):
    """健康检查响应。"""

    status: str = "ok"
