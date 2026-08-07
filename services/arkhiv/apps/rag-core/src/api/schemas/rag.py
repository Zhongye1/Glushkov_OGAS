from pydantic import BaseModel, Field


class Chunk(BaseModel):
    """检索命中的片段，含可溯源信息。"""

    text: str
    source_path: str
    line_range: tuple[int, int] | None = None
    score: float = 0.0
    source_url: str | None = None


class Answer(BaseModel):
    """带引用的生成回答。"""

    text: str
    citations: list[Chunk] = Field(default_factory=list)
    usage: dict[str, int] = Field(default_factory=dict)


class RetrieveRequest(BaseModel):
    query: str = Field(min_length=1)
    top_k: int = Field(default=10, ge=1, le=100)
    filters: dict[str, str] | None = None


class AnswerRequest(RetrieveRequest):
    stream: bool = False
