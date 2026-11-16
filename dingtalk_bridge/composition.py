"""Explicit ordered rich-text images through the pinned official Markdown route.

Only generated, digest-staged image references reach DWS. This does not promise
native image cards, original downloads in the client, or ordinary file bundles.
"""
import hashlib
import os
from pathlib import Path
import re
import string
import tempfile

from .text_limits import PERSONAL_TEXT_UNITS, utf16_units

IMAGE_LIMIT = 2 * 1024 * 1024


class ArtifactIntegrityError(ValueError):
    """The intended bytes changed before any new delivery was reserved."""
    def __init__(self):
        super().__init__('artifact_integrity_mismatch')


def markdown(payload):
    # A caller supplies literal text, never Markdown/HTML or upload destinations.
    escaped = ''.join('\\' + c if c in string.punctuation else c for c in payload['text'])
    images = [f'![image {i}]({item["staged"]})' for i, item in enumerate(payload['images'], 1)]
    return '\n\n'.join(([escaped] if escaped else []) + images)


def prepare(root, local, value):
    if not isinstance(value, dict) or set(value) - {'text', 'images'}:
        raise ValueError('composition requires text and an ordered images array')
    text = value.get('text', '')
    if not isinstance(text, str) or '\x00' in text or len(text.encode()) > 65536:
        raise ValueError('composition text must be a literal string up to 64 KiB without NUL')
    images = value.get('images')
    if not isinstance(images, list) or not 1 <= len(images) <= 9:
        raise ValueError('composition requires 1-9 PNG/JPEG image references')
    payload = {'kind': 'composition', 'text': text, 'images': []}
    sources = []
    for item in images:
        if not isinstance(item, dict) or set(item) != {'path', 'sha256'}:
            raise ValueError('Each composition image requires only path and sha256')
        name, digest = item['path'], item['sha256']
        if not isinstance(name, str) or not name or '\x00' in name:
            raise ValueError('Image path must be a safe project relative path')
        path = Path(name)
        source = (root / path).resolve()
        allowed = [(root / 'fixtures').resolve(), (root / 'local/outbox').resolve()]
        if path.is_absolute() or '..' in path.parts or not any(source.is_relative_to(p) for p in allowed):
            raise ValueError('Only images in fixtures/ or local/outbox/ can be composed')
        if source.suffix.lower() not in {'.png', '.jpg', '.jpeg'}:
            raise ValueError('composition accepts PNG/JPEG only')
        if not isinstance(digest, str) or re.fullmatch(r'[0-9a-f]{64}', digest) is None:
            raise ValueError('Each image requires its expected lowercase SHA256')
        staged = local / 'staged' / digest / ('image' + source.suffix.lower())
        payload['images'].append({'name': source.name, 'sha256': digest, 'staged': str(staged.relative_to(root))})
        sources.append(source)
    if utf16_units(markdown(payload)) > PERSONAL_TEXT_UNITS:
        raise ValueError('Generated composition exceeds 5120 UTF-16 units; shorten text or use fewer images')
    return payload, sources


def stage(root, payload, sources):
    # Read/validate all originals before staging any or reserving a delivery.
    originals = []
    for item, source in zip(payload['images'], sources):
        if not source.is_file() or source.stat().st_size > IMAGE_LIMIT:
            raise ValueError('Each composition image must be a file <=2 MiB without compression')
        with source.open('rb') as handle:
            content = handle.read(IMAGE_LIMIT + 1)
        if len(content) > IMAGE_LIMIT:
            raise ValueError('Each composition image must be <=2 MiB without compression')
        if hashlib.sha256(content).hexdigest() != item['sha256']:
            raise ArtifactIntegrityError()
        signature = b'\x89PNG\r\n\x1a\n' if source.suffix.lower() == '.png' else b'\xff\xd8\xff'
        if not content.startswith(signature):
            raise ValueError('Image content does not match PNG/JPEG extension')
        originals.append(content)
    for item, content in zip(payload['images'], originals):
        target = root / item['staged']
        target.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        if target.parent.resolve() != target.parent or target.is_symlink():
            raise ValueError('Staged image must not traverse a symlink')
        # Publish atomically without overwriting an existing content-addressed file.
        if not target.exists():
            with tempfile.NamedTemporaryFile(dir=target.parent, delete=False) as handle:
                temporary = Path(handle.name)
                try:
                    handle.write(content); handle.flush(); os.fsync(handle.fileno())
                    try: os.link(temporary, target)
                    except FileExistsError: pass
                finally:
                    temporary.unlink()
        if target.is_symlink() or not target.is_file() or target.stat().st_size != len(content):
            raise ValueError('Staged image integrity mismatch; no upload or send attempted')
        if hashlib.sha256(target.read_bytes()).hexdigest() != item['sha256']:
            raise ValueError('Staged image integrity mismatch; no upload or send attempted')
