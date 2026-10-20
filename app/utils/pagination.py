import math

from pydantic import BaseModel, Field


class PaginationParams(BaseModel):
    page: int = Field(1, ge=1, le=10000, description="Page number")
    limit: int = Field(20, ge=1, le=100, description="Items per page")

    @property
    def offset(self) -> int:
        return (self.page - 1) * self.limit


def paginate_response(items: list, total: int, page: int, limit: int) -> dict:
    total_pages = math.ceil(total / limit) if limit > 0 else 0
    return {
        "items": items,
        "total": total,
        "page": page,
        "limit": limit,
        "total_pages": total_pages,
    }
