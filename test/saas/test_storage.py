from pathlib import Path

import pytest

from shared.security.filenames import safe_filename, safe_object_key
from shared.storage.local import LocalStorageProvider


def test_safe_filename_strips_traversal():
    assert safe_filename("../etc/passwd") == "passwd"
    assert safe_filename("..\\secret.txt") == "secret.txt"
    assert safe_filename("") == "upload.bin"


def test_safe_object_key_rejects_empty():
    with pytest.raises(ValueError):
        safe_object_key("../..")


def test_local_storage_rejects_escape(tmp_path: Path):
    provider = LocalStorageProvider(tmp_path)
    sample = tmp_path / "in.txt"
    sample.write_text("ok", encoding="utf-8")
    key = provider.upload_file(str(sample), "workspaces/ws1/videos/v1/final.mp4")
    assert provider.exists(key)
    assert (tmp_path / "workspaces" / "ws1" / "videos" / "v1" / "final.mp4").is_file()
    escaped = provider.upload_file(str(sample), "../outside.mp4")
    assert escaped == "outside.mp4"
    assert (tmp_path / "outside.mp4").is_file()
    assert not (tmp_path.parent / "outside.mp4").exists()
