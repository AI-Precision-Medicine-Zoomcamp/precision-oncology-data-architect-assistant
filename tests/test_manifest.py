from pathlib import Path
import yaml


def test_source_manifest_exists():
    path = Path("data/source_manifest.yaml")
    assert path.exists()
    data = yaml.safe_load(path.read_text())
    assert "collections" in data
    assert "mcode" in data["collections"]
