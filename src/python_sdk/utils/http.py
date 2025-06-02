from collections.abc import Mapping, Sequence
from typing import Any, Callable, Optional, Union, override

from aiolimiter import AsyncLimiter
from httpx import URL, USE_CLIENT_DEFAULT, AsyncClient, Limits, Proxy, Response, Timeout
from httpx import Response as HTTPResponse
from httpx import _types as types  # noqa
from httpx._client import UseClientDefault  # noqa

from ..conf import constants


def extract_http_response_body(response: HTTPResponse) -> Any:
    try:
        return response.json()
    except Exception:  # noqa
        return response.text


class HttpClient(AsyncClient):
    rate_limiter: AsyncLimiter

    def __init__(
        self,
        *,
        base_url: Optional[URL | str] = None,
        api_access_token: Optional[str] = None,
        timeout: float
        | None
        | tuple[float | None, float | None, float | None, float | None]
        | Timeout = constants.DEFAULT_TIMEOUT_CONFIG,
        limits: Limits = constants.DEFAULT_LIMITS,
        proxy: URL | str | Proxy | None = None,
        event_hooks: None | (Mapping[str, list[Callable[..., Any]]]) = None,
        max_rate: int = 10,
        time_period: float = 1.0,
    ):
        super().__init__(
            headers={"api_access_token": api_access_token},
            proxy=proxy,
            timeout=timeout,
            limits=limits,
            event_hooks=event_hooks,
            base_url=URL(base_url) if base_url is not None else None,
        )
        self.rate_limiter = AsyncLimiter(max_rate=max_rate, time_period=time_period)

    @override
    async def request(
        self,
        method: str,
        url: URL | str,
        *,
        content: types.RequestContent | None = None,
        data: dict[str, Any] | None = None,
        files: Union[
            Mapping[str, types.FileTypes], Sequence[tuple[str, types.FileTypes]] | None
        ] = None,
        json: Any | None = None,
        params: types.QueryParamTypes | None = None,
        headers: types.HeaderTypes | None = None,
        cookies: types.CookieTypes | None = None,
        auth: types.AuthTypes | UseClientDefault | None = USE_CLIENT_DEFAULT,
        follow_redirects: bool | UseClientDefault = USE_CLIENT_DEFAULT,
        timeout: types.TimeoutTypes | UseClientDefault = USE_CLIENT_DEFAULT,
        extensions: types.RequestExtensions | None = None,
    ) -> Response:
        async with self.rate_limiter:
            return await super().request(
                method,
                url,
                content=content,
                data=data,
                files=files,
                json=json,
                params=params,
                headers=headers,
                cookies=cookies,
                auth=auth,
                follow_redirects=follow_redirects,
                timeout=timeout,
                extensions=extensions,
            )
