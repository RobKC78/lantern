"""Build an architecture-independent Debian package using distribution Python.

Runs on Windows or Linux; no native binaries are cross-compiled.
Linux installation/runtime validation is a separate release gate.
"""
import argparse
import gzip
import io
from pathlib import Path
import tarfile


def tar(entries):
    buffer = io.BytesIO()
    with tarfile.open(fileobj=buffer, mode='w', format=tarfile.USTAR_FORMAT) as archive:
        for name, data, mode in entries:
            info = tarfile.TarInfo('./' + name)
            info.size, info.mode = len(data), mode
            info.uid = info.gid = 0
            info.uname = info.gname = 'root'
            archive.addfile(info, io.BytesIO(data))
    return gzip.compress(buffer.getvalue(), mtime=0)


def build(destination):
    root = Path(__file__).resolve().parents[1]
    entries = []
    for path in sorted((root / 'lantern').rglob('*')):
        if path.is_file() and '__pycache__' not in path.parts and path.suffix in ('.py', '.js', '.html', '.css'):
            entries.append(('usr/lib/lantern/' + path.relative_to(root).as_posix(), path.read_bytes(), 0o644))
    entries.append(('usr/lib/lantern/run.py', (root / 'run.py').read_bytes(), 0o644))
    entries.append(('usr/bin/lantern', b'#!/bin/sh\nexec /usr/bin/python3 -B /usr/lib/lantern/run.py "$@"\n', 0o755))
    entries.append(('usr/share/applications/lantern.desktop',
        b'[Desktop Entry]\nType=Application\nName=Lantern Diagnostics\nComment=Check this computer and explain problems\nExec=/usr/bin/lantern\nIcon=utilities-system-monitor\nTerminal=true\nCategories=System;Utility;\nStartupNotify=false\n', 0o644))
    for name in ('README.md', 'REPAIRS.md', 'AI-SERVICE.md'):
        entries.append(('usr/share/doc/lantern-diagnostics/' + name, (root / name).read_bytes(), 0o644))
    control = ('Package: lantern-diagnostics\nVersion: 0.1.0\nSection: utils\nPriority: optional\n'
        'Architecture: all\nMaintainer: Lantern Local Build <lantern@localhost>\n'
        'Depends: python3 (>= 3.10), python3-psutil (>= 5.9), iproute2\n'
        'Recommends: pciutils, policykit-1, xdg-utils\n'
        f'Installed-Size: {(sum(len(data) for _, data, _ in entries) + 1023) // 1024}\n'
        'Description: Local computer diagnostics with a browser dashboard\n'
        ' Explains system findings and offers reviewed service repairs.\n'
        ' Optional AI research requires a separately configured service.\n').encode()
    members = [('debian-binary', b'2.0\n'), ('control.tar.gz', tar([('control', control, 0o644)])),
               ('data.tar.gz', tar(entries))]
    destination.parent.mkdir(parents=True, exist_ok=True)
    with destination.open('wb') as output:
        output.write(b'!<arch>\n')
        for name, data in members:
            output.write(f'{name + "/":<16}{0:<12}{0:<6}{0:<6}{"100644":<8}{len(data):<10}`\n'.encode('ascii'))
            output.write(data)
            if len(data) % 2:
                output.write(b'\n')
    # Reopen the actual result and check package members, permissions and payload.
    with destination.open('rb') as package:
        assert package.read(8) == b'!<arch>\n'
        for expected_name, expected_data in members:
            header = package.read(60)
            assert header[:16].decode().strip().rstrip('/') == expected_name
            size = int(header[48:58])
            assert package.read(size) == expected_data
            if size % 2:
                assert package.read(1) == b'\n'
    with tarfile.open(fileobj=io.BytesIO(members[2][1]), mode='r:gz') as archive:
        assert archive.getmember('./usr/bin/lantern').mode == 0o755
        assert archive.extractfile('./usr/lib/lantern/run.py').read() == (root / 'run.py').read_bytes()
        assert archive.getmember('./usr/lib/lantern/lantern/ui/index.html')
        assert all(not n.startswith('/') and '..' not in n.split('/') for n in archive.getnames())
    print(f'Built and checked package structure: {destination}')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', type=Path, default=Path('dist/Lantern-0.1.0_all.deb'))
    build(parser.parse_args().output)
