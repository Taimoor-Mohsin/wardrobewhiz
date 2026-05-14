from pydantic import BaseModel, field_validator


class FeedbackRequest(BaseModel):
    outfit_id: int
    rating: int  # must be +1 or -1

    @field_validator("rating")
    @classmethod
    def rating_must_be_valid(cls, v: int) -> int:
        if v not in (1, -1):
            raise ValueError("rating must be 1 or -1")
        return v


class FeedbackResponse(BaseModel):
    message: str
