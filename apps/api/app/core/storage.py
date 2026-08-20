import httpx

from app.core.config import settings


class StorageError(Exception):
    """Raised on any non-2xx response from Supabase Storage — callers translate this to
    whatever HTTP status makes sense for their endpoint rather than leaking transport details."""


def _base_url() -> str:
    return f"{settings.supabase_url.rstrip('/')}/storage/v1"


def _headers() -> dict[str, str]:
    # Service-role key — Storage access here is always server-to-server (upload during the
    # authenticated upload endpoint, download inside the worker), never exposed to the browser.
    return {
        "Authorization": f"Bearer {settings.supabase_secret_key}",
        "apikey": settings.supabase_secret_key,
    }


async def upload_object(path: str, content: bytes, content_type: str) -> None:
    """`path` is `<bucket>/<key>`. Uses upsert so a retry after a partial failure overwrites
    cleanly instead of 409ing on an already-existing object."""
    bucket, _, key = path.partition("/")
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(
            f"{_base_url()}/object/{bucket}/{key}",
            headers={**_headers(), "Content-Type": content_type, "x-upsert": "true"},
            content=content,
        )
    if response.status_code >= 400:
        raise StorageError(f"Upload failed ({response.status_code}): {response.text}")


async def download_object(path: str) -> bytes:
    bucket, _, key = path.partition("/")
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.get(f"{_base_url()}/object/{bucket}/{key}", headers=_headers())
    if response.status_code >= 400:
        raise StorageError(f"Download failed ({response.status_code}): {response.text}")
    return response.content


async def delete_object(path: str) -> None:
    bucket, _, key = path.partition("/")
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.delete(f"{_base_url()}/object/{bucket}/{key}", headers=_headers())
    if response.status_code >= 400:
        raise StorageError(f"Delete failed ({response.status_code}): {response.text}")


async def create_signed_url(path: str, *, expires_in: int = 3600) -> str:
    """Resumes are personal documents — the bucket is private, so the frontend never gets a
    permanent public URL, only a short-lived signed one generated on demand."""
    bucket, _, key = path.partition("/")
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(
            f"{_base_url()}/object/sign/{bucket}/{key}",
            headers=_headers(),
            json={"expiresIn": expires_in},
        )
    if response.status_code >= 400:
        raise StorageError(f"Signing failed ({response.status_code}): {response.text}")
    signed_path = response.json()["signedURL"]
    return f"{settings.supabase_url.rstrip('/')}/storage/v1{signed_path}"
