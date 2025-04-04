from collections.abc import Iterator
from typing import Literal, Optional, Protocol, TypedDict


class FileWithContent(TypedDict):
    filename: str
    content: str | bytes


class StorageProtocol(Protocol):
    def get_file_content(self, filename: str) -> bytes: ...

    def download_file(self, filename: str, destination: str) -> None: ...

    def upload_file(self, filename: str, destination: str) -> None: ...

    def delete_file(self, filename: str) -> None: ...

    def list_files(self, prefix: str) -> list[str]: ...

    def download_directory(self, prefix: str, destination: str) -> None: ...

    def upload_directory(self, source: str, destination: str) -> None: ...

    def get_files(self, prefix: str) -> Iterator[FileWithContent]: ...  # type: ignore

    def find_and_download_file(
            self, file_name: str, fmt: Literal["str", "bytes"] = "bytes"
    ) -> Optional[bytes | str]:...
