"""Static frontend serving with a single-page-app fallback.

React routes such as /settings exist only in the browser. Reloading one of
them asked the backend for a file that does not exist and returned
{"detail":"Not Found"}. This serves index.html for those paths instead,
while unknown /api/* paths and missing asset files (anything with a file
extension) keep their normal 404.
"""
from __future__ import annotations

from starlette.exceptions import HTTPException
from starlette.staticfiles import StaticFiles


class SPAStaticFiles(StaticFiles):
    async def get_response(self, path: str, scope):
        try:
            return await super().get_response(path, scope)
        except HTTPException as exc:
            if exc.status_code != 404 or not _is_client_route(path):
                raise
            return await super().get_response("index.html", scope)


def _is_client_route(path: str) -> bool:
    # Starlette builds this path with os.path, so on Windows it uses "\\".
    clean = path.replace("\\", "/").strip("/")
    if clean == "api" or clean.startswith("api/"):
        return False
    last = clean.rsplit("/", 1)[-1]
    return "." not in last
