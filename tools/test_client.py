from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import client

class ClientTests(unittest.TestCase):
    def test_safe_path(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.assertEqual(client.safe(root, 'mods/a.jar'), root / 'mods/a.jar')
            for value in ['../secret', '/absolute', 'C:/absolute', 'a\\b', 'a/../../secret']:
                with self.subTest(value=value), self.assertRaises(ValueError):
                    client.safe(root, value)

    def test_verify_corruption(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            p = root / 'asset'; p.write_bytes(b'ok')
            lock = {'files': [{'path': 'asset', 'size': 2, 'sha256': client.sha(p)}], 'external': [], 'textFiles': []}
            with patch.object(client, 'GAME', root):
                client.verify(lock)
                p.write_bytes(b'no')
                with self.assertRaises(RuntimeError):
                    client.verify(lock)

    def test_cached_download(self):
        with tempfile.TemporaryDirectory() as directory:
            p = Path(directory) / 'file'; p.write_bytes(b'ok')
            with patch.object(client.urllib.request, 'urlopen', side_effect=AssertionError('network')):
                self.assertEqual(client.download({'sha256': client.sha(p)}, p), p)

if __name__ == '__main__':
    unittest.main()
