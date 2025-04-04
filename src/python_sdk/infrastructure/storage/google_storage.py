from collections.abc import Iterator
from typing import Literal, Optional

from google.cloud import storage
from google.cloud.storage import Bucket, Client

from ...conf import settings
from ...utils.decorators import singleton
from .storage_protocol import FileWithContent, StorageProtocol


@singleton
class GoogleStorage(StorageProtocol):
    def __init__(self) -> None:
        """
        Initializes the GCSService class.

        """

        self.client: Client = storage.Client.from_service_account_info(
            info=settings.gcp.credentials
        )
        self.bucket: Bucket = self.client.get_bucket(settings.gcp.bucket_name)

    def list_objects(self, prefix: Optional[str] = None) -> list[str]:
        """
        Lists all objects in the bucket or within a specified prefix.
        Args:
            prefix: Folder path or prefix to filter objects (optional).

        Returns:
            List of object names.
        """
        return [b for b in self.bucket.list_blobs(prefix=prefix)]

    def get_file_content(self, filename: str) -> bytes:
        return self.find_and_download_file(file_name=filename, fmt="bytes")

    def get_files(self, prefix: str) -> Iterator[FileWithContent]:
        for blob in self.bucket.list_blobs(prefix=prefix):
            yield {
                "filename": blob.name,
                "content": blob.download_as_text(),
            }

    def find_and_download_file(
        self, file_name: str, fmt: Literal["str", "bytes"] = "bytes"
    ) -> Optional[bytes | str]:
        """
        Searches for a file in the bucket recursively using an async iterator, downloads it, and returns its content.

        Args:
            file_name: The name of the file to search for in the bucket.
            fmt: The format to return the file content in. Can be "str" or "bytes".

        Returns:
            The file content as a string (if encoding is provided) or bytes. Returns None if the file is not found.
        """
        for blob in self.bucket.list_blobs():
            if blob.name.endswith(file_name):
                return (
                    blob.download_as_text()
                    if fmt == "str"
                    else blob.download_as_bytes()
                )
