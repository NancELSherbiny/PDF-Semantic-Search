import pytest

from app.api.routes.ingest import _read_path
from app.core.exceptions import BadRequestError


def test_read_path_rejects_paths_outside_base_dir():
    # Default base is /data; anything outside it must be rejected so a caller
    # cannot read arbitrary files off the server.
    with pytest.raises(BadRequestError):
        _read_path("/etc")
