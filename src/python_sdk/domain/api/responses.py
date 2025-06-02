from typing import Optional

from pydantic import Field

from ..base.base_model import BaseModel


class APIResponse(BaseModel):
    status: str = Field(
        default="ok", title="Status", description="The status of the response"
    )
    status_code: int = Field(
        default=200, title="Status code", description="The status code of the response"
    )


class APIResponse20OK(APIResponse):
    pass


class APIHealthResponse(APIResponse):
    pass


class APIResponse500InternalServerError(APIResponse):
    status: str = Field(
        default="error", title="Status", description="The status code of the response"
    )
    status_code: int = Field(
        default=500, title="Status code", description="The status code of the response"
    )
    error: Optional[str] = Field(
        default=None, title="Error", description="The error message of the response"
    )


class APIResponse404NotFound(APIResponse):
    status: str = Field(
        default="error", title="Status", description="The status code of the response"
    )
    status_code: int = Field(
        default=404, title="Status code", description="The status code of the response"
    )
    error: Optional[str] = Field(
        default=None, title="Error", description="The error message of the response"
    )


class APIErrorResponse(APIResponse):
    status: str = Field(
        default="error", title="Status", description="The status code of the response"
    )
    status_code: int = Field(
        default=500, title="Status code", description="The status code of the response"
    )
    error: Optional[str] = Field(
        default=None, title="Error", description="The error message of the response"
    )
