"""Package the portable Python sources for pacman; no native cross compilation."""
import argparse
import importlib.util
import io
from pathlib import Path
import tarfile
import tempfile


def build(output):
    # Share the exact application payload and launcher with the Debian builder.
    spec = importlib.util.spec_from_file_location('deb', Path(__file__).with_name('build-linux-deb.py'))
    deb = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(deb)
    with tempfile.TemporaryDirectory() as temporary:
        intermediate = Path(temporary) / 'payload.deb'
        deb.build(intermediate)
        with intermediate.open('rb') as stream:
            assert stream.read(8) == b'!<arch>\n'
            for _ in range(3):
                header = stream.read(60)
                size = int(header[48:58])
                data = stream.read(size)
                if size % 2:
                    stream.read(1)
                if header[:16].decode().strip().rstrip('/') == 'data.tar.gz':
                    payload = data
    with tarfile.open(fileobj=io.BytesIO(payload), mode='r:gz') as archive:
        entries = [(m.name.removeprefix('./'), archive.extractfile(m).read(), m.mode) for m in archive.getmembers()]
    size = sum(len(data) for _, data, _ in entries)
    metadata = (f'pkgname = lantern-diagnostics\npkgbase = lantern-diagnostics\npkgver = 0.1.0-1\n'
                'pkgdesc = Local diagnostics dashboard with reviewed repairs and optional AI research\n'
                f'builddate = 1788480000\npackager = Lantern Local Build\nsize = {size}\narch = any\n'
                'depend = python>=3.10\ndepend = python-psutil>=5.9\ndepend = iproute2\n'
                'optdepend = pciutils: PCI and driver inventory\n'
                'optdepend = polkit: administrator approval for supported repairs\n'
                'optdepend = xdg-utils: open the dashboard in your browser\n').encode()
    entries.insert(0, ('.PKGINFO', metadata, 0o644))
    output.parent.mkdir(parents=True, exist_ok=True)
    # gzip is supported by pacman; do not label gzip bytes as zstd.
    with tarfile.open(output, 'w:gz', format=tarfile.USTAR_FORMAT) as archive:
        for name, data, mode in entries:
            info = tarfile.TarInfo(name)
            info.size, info.mode = len(data), mode
            info.uid = info.gid = 0
            info.uname = info.gname = 'root'
            archive.addfile(info, io.BytesIO(data))
    with tarfile.open(output, 'r:gz') as archive:
        assert archive.extractfile('.PKGINFO').read() == metadata
        assert archive.getmember('usr/bin/lantern').mode == 0o755
        assert archive.extractfile('usr/lib/lantern/lantern/ui/index.html').read()
        assert all(not n.startswith('/') and '..' not in n.split('/') for n in archive.getnames())
    print(f'Built and structure-checked: {output}. CachyOS installation remains untested.')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', type=Path, default=Path('dist/lantern-diagnostics-0.1.0-1-any.pkg.tar.gz'))
    build(parser.parse_args().output)
