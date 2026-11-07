"""Re-run the static checks of reviews/2026-11-08_make-automation-source-snapshot_code-review.md.

Reads the ZIP as data only. Never imports or executes any file from the package.
Usage: python -I verify_make_snapshot.py <zip> [SHA256SUMS.txt]
"""
import ast
import hashlib
import json
import pathlib
import stat
import sys
import tempfile
import zipfile

LAUNCHER = ('parallel/make-collaboration/positive-smoke-plan-20261107/source-resume-1/'
            'native-local-verification-1/worker/launcher.py')


def sha256(data):
    return hashlib.sha256(data).hexdigest()


def extract(archive, dest):
    names = [info.filename for info in archive.infolist()]
    if len(names) != len(set(names)):
        raise ValueError('duplicate entry names')
    for info in archive.infolist():
        target = (dest / info.filename).resolve()
        if not target.is_relative_to(dest):
            raise ValueError(f'path escape: {info.filename}')
        if stat.S_ISLNK(info.external_attr >> 16):
            raise ValueError(f'symlink entry: {info.filename}')
    archive.extractall(dest)
    return len(names)


def manifest_mismatches(root):
    manifest = json.loads((root / 'MANIFEST.json').read_text(encoding='utf-8'))
    listed = {entry['path']: entry for entry in manifest['files']}
    actual = {str(p.relative_to(root)).replace('\\', '/') for p in root.rglob('*') if p.is_file()}
    bad = [path for path, entry in listed.items()
           if not (root / path).is_file()
           or (root / path).stat().st_size != entry['bytes']
           or sha256((root / path).read_bytes()) != entry['sha256']]
    return len(listed), bad, sorted(actual - set(listed) - {'MANIFEST.json'})


def python_facts(root):
    sources = sorted(root.rglob('*.py'))
    syntax_errors, tests, skips = [], 0, []
    for path in sources:
        try:
            tree = ast.parse(path.read_text(encoding='utf-8'))
        except SyntaxError as error:
            syntax_errors.append(f'{path.relative_to(root)}: {error}')
            continue
        if not path.name.startswith('test_'):
            continue
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name.startswith('test'):
                tests += 1
            if isinstance(node, (ast.Call, ast.Attribute, ast.Name)) and 'skip' in ast.unparse(node).lower():
                skips.append(f'{path.name}:{node.lineno}')
    return len(sources), syntax_errors, tests, sorted(set(skips))


def launcher_pins(root):
    tree = ast.parse((root / LAUNCHER).read_text(encoding='utf-8'))
    expected = next(ast.literal_eval(node.value) for node in ast.walk(tree)
                    if isinstance(node, ast.Assign)
                    and getattr(node.targets[0], 'id', None) == 'EXPECTED')
    base = root / 'parallel/make-collaboration'
    return {name: sha256((base / relative).resolve().read_bytes()) == digest
            for name, (relative, digest) in expected.items()}


def main(argv):
    if len(argv) not in (2, 3):
        print(__doc__)
        return 2
    zip_path = pathlib.Path(argv[1])
    report = {'zip_sha256': sha256(zip_path.read_bytes()), 'zip_bytes': zip_path.stat().st_size}
    if len(argv) == 3:
        sums = dict(reversed(line.split(None, 1)) for line in
                    pathlib.Path(argv[2]).read_text(encoding='utf-8').splitlines() if line.strip())
        report['sha256sums_match'] = report['zip_sha256'] in sums.values()
    with zipfile.ZipFile(zip_path) as archive, tempfile.TemporaryDirectory() as temp:
        report['crc_first_bad_entry'] = archive.testzip()
        root = pathlib.Path(temp).resolve()
        report['entries'] = extract(archive, root)
        listed, bad, unlisted = manifest_mismatches(root)
        report.update(manifest_entries=listed, manifest_mismatches=bad, unlisted_files=unlisted)
        py_files, syntax_errors, tests, skips = python_facts(root)
        report.update(python_files=py_files, syntax_errors=syntax_errors,
                      test_functions=tests, skip_markers=skips)
        report['launcher_pins_match'] = launcher_pins(root)
    passed = (report.get('sha256sums_match', True) and report['crc_first_bad_entry'] is None
              and not bad and not syntax_errors and all(report['launcher_pins_match'].values()))
    report['all_static_checks_passed'] = passed
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if passed else 1


if __name__ == '__main__':
    raise SystemExit(main(sys.argv))
