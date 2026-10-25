"""Guard the Docker/pip dependency interface against authored-metadata drift."""
import importlib.util
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("export_requirements", ROOT / "scripts/export_requirements.py")
export = importlib.util.module_from_spec(spec)
spec.loader.exec_module(export)


class DependencyManifestTests(unittest.TestCase):
    def test_committed_docker_manifest_matches_authored_metadata(self):
        self.assertEqual(export.main(["--check"]), 0)

    def test_stale_check_does_not_overwrite_the_file(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "pyproject.toml").write_text('[project]\ndependencies=["a[extra]>=2", "b @ https://example.test/b.whl"]\n')
            output = root / "requirements.txt"
            output.write_text("stale\n")
            with patch.object(export, "ROOT", root):
                self.assertEqual(export.main(["--check"]), 1)
                self.assertEqual(output.read_text(), "stale\n")
                self.assertEqual(export.main([]), 0)
                self.assertEqual(export.main(["--check"]), 0)
            self.assertIn("a[extra]>=2\nb @ https://example.test/b.whl\n", output.read_text())


if __name__ == "__main__":
    unittest.main()
