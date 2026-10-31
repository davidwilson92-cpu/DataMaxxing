"""Small private list previews. Originals remain the source for editing/publishing."""
import base64
from hashlib import sha256
import io
import os
from threading import BoundedSemaphore
import warnings

from PIL import Image, ImageOps
from . import read_cache, storage

# Bound decoding memory on the existing small host, independently of AI/publishing.
_decode_slot = BoundedSemaphore(1)


def image_preview(asset):
    if not 0 < asset.size_bytes <= 15 * 1024 * 1024:
        raise ValueError('Unsupported image size')
    remote = asset.storage_key.startswith('nova/') and os.environ.get('S3_BUCKET')
    if remote:
        metadata = storage._s3_client().head_object(Bucket=os.environ['S3_BUCKET'], Key=asset.storage_key)
        size = metadata['ContentLength']
        version = metadata.get('VersionId') or metadata.get('ETag')
    else:
        stat = storage.local_path(asset.storage_key).stat()
        size = stat.st_size
        version = (stat.st_ino, stat.st_size, stat.st_mtime_ns, stat.st_ctime_ns)
    if size != asset.size_bytes:
        raise ValueError('Image unavailable')
    fingerprint = sha256(repr((asset.storage_key, version)).encode()).hexdigest()
    key = (asset.user_id, asset.brand_id, 'thumbnail', asset.id, fingerprint)

    def render():
        with _decode_slot:
            data = storage.get_bytes(asset.storage_key)
            if len(data) != size:
                raise ValueError('Image changed during read')
            with warnings.catch_warnings():
                warnings.simplefilter('error', Image.DecompressionBombWarning)
                with Image.open(io.BytesIO(data)) as original:
                    if original.width * original.height > 40_000_000:
                        raise ValueError('Unsupported dimensions')
                    original.draft('RGB', (512, 512))
                    image = ImageOps.exif_transpose(original)
                    image.thumbnail((256, 256), Image.Resampling.LANCZOS)
                    if image.mode in ('RGBA', 'LA') or 'transparency' in image.info:
                        rgba = image.convert('RGBA')
                        image = Image.new('RGB', rgba.size, 'white')
                        image.paste(rgba, mask=rgba.getchannel('A'))
                    else:
                        image = image.convert('RGB')
                    output = io.BytesIO()
                    image.save(output, format='JPEG', quality=80)
            return base64.b64encode(output.getvalue()).decode('ascii')

    # Remote objects without a version must be read afresh. No permanent derivative
    # files, credentials or public image URLs are retained.
    encoded = read_cache.load(key, render, refresh=not bool(version))
    return base64.b64decode(encoded)
