"""The GitHub-Actions import route must refuse any file whose checksum doesn't match."""
import hashlib
import json

import pytest

from cricintel.sources.cricsheet import import_verified


def _branch(tmp_path, tamper=False):
    (tmp_path / "downloads").mkdir()
    (tmp_path / "register").mkdir()
    (tmp_path / "downloads" / "ipl_json.zip").write_bytes(b"zipbytes")
    (tmp_path / "register" / "people.csv").write_bytes(b"identifier,name\n")
    lines = [f"{hashlib.sha256(p.read_bytes()).hexdigest()}  {p.relative_to(tmp_path)}"
             for p in sorted(tmp_path.rglob("*")) if p.is_file()]
    (tmp_path / "SHA256SUMS").write_text("\n".join(lines) + "\n")
    (tmp_path / "PROVENANCE.json").write_text(json.dumps({"source": "Cricsheet"}))
    if tamper:
        (tmp_path / "downloads" / "ipl_json.zip").write_bytes(b"tampered")
    return tmp_path


def test_import_accepts_matching(tmp_path):
    m = import_verified(_branch(tmp_path))
    assert set(m["files"]) == {"downloads/ipl_json.zip", "register/people.csv"}


def test_import_rejects_tampered(tmp_path):
    with pytest.raises(SystemExit, match="CHECKSUM MISMATCH"):
        import_verified(_branch(tmp_path, tamper=True))
