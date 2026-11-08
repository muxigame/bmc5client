"""Generate the Windows GLFW option from this installation, never a developer path."""
from pathlib import Path
import hashlib, os, platform


def write_options(game, lock):
    fix = lock.get('clientNativeFix')
    if not fix or os.name != 'nt' or platform.machine().lower() not in ('amd64', 'x86_64'):
        return None
    dll = game / fix['path']
    if not dll.resolve().is_relative_to(game.resolve()):
        raise ValueError('Native fix must belong to this installation')
    if not dll.is_file() or hashlib.sha256(dll.read_bytes()).hexdigest() != fix['sha256']:
        raise RuntimeError('Pinned Windows native fix is missing or modified')
    out = game / 'city-core-jvm-options.txt'
    marker = '# Generated city-core options; paths follow this installation.\n'
    if out.exists() and not out.read_text('utf8').startswith(marker):
        raise RuntimeError('Preserve authored JVM options; choose another file: ' + str(out))
    out.write_text(marker + '"-Dorg.lwjgl.glfw.libname=' + dll.resolve().as_posix() + '"\n', 'utf8')
    return out
