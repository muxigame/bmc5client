from pathlib import Path
import hashlib,tempfile,unittest
from unittest.mock import patch
import native_options as native


class NativeOptionsTests(unittest.TestCase):
    def test_paths_follow_moved_install_and_original_dll_unchanged(self):
        with tempfile.TemporaryDirectory() as d:
            game=Path(d)/'a folder';dll=game/'native-fixes/glfw.dll'
            dll.parent.mkdir(parents=True);dll.write_bytes(b'owned')
            lock={'clientNativeFix':{'path':'native-fixes/glfw.dll','sha256':hashlib.sha256(b'owned').hexdigest()}}
            with patch.object(native.os,'name','nt'),patch.object(native.platform,'machine',return_value='AMD64'):
                out=native.write_options(game,lock)
                self.assertIn(dll.resolve().as_posix(),out.read_text())
                self.assertNotIn('D:/CPN',out.read_text())
                self.assertEqual(dll.read_bytes(),b'owned')
                out.write_text('my options')
                with self.assertRaises(RuntimeError):native.write_options(game,lock)
                self.assertEqual(out.read_text(),'my options')

    def test_platform_without_override_and_checksum_rejection(self):
        with tempfile.TemporaryDirectory() as d:
            game=Path(d);lock={'clientNativeFix':{'path':'glfw.dll','sha256':'0'*64}}
            with patch.object(native.os,'name','posix'):self.assertIsNone(native.write_options(game,lock))
            with patch.object(native.os,'name','nt'),patch.object(native.platform,'machine',return_value='AMD64'):
                with self.assertRaises(RuntimeError):native.write_options(game,lock)
            self.assertFalse((game/'city-core-jvm-options.txt').exists())

if __name__=='__main__':unittest.main()
