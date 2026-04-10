from pydantic import BaseModel


class TagCount(BaseModel):
    tag: str
    count: int


class DayVolume(BaseModel):
    date: str
    count: int


class AnalyticsResponse(BaseModel):
    total_processed: int
    by_status: dict[str, int]
    approval_rate: float
    common_tags: list[TagCount]
    avg_processing_time_ms: float
    volume_by_day: list[DayVolume]
