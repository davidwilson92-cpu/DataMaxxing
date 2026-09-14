"""Validate bounded media before persisting any part of an upload batch."""
import io
import warnings
import av
from PIL import Image, UnidentifiedImageError
from fastapi import HTTPException

IMAGE_TYPES={'image/jpeg':'JPEG','image/png':'PNG','image/gif':'GIF','image/webp':'WEBP'}
VIDEO_TYPES={'video/mp4','video/quicktime','video/webm'}


async def validated_upload(file):
    mime=(file.content_type or '').lower()
    if mime not in IMAGE_TYPES and mime not in VIDEO_TYPES:
        raise HTTPException(400,'Choose a JPEG, PNG, GIF, WebP, MP4, MOV or WebM file.')
    limit=(100 if mime in VIDEO_TYPES else 15)*1024*1024
    content=bytearray()
    while chunk:=await file.read(1024*1024):
        if len(content)+len(chunk)>limit:
            raise HTTPException(413,'Images must be 15 MB or smaller; videos 100 MB or smaller.')
        content.extend(chunk)
    data=bytes(content)
    from starlette.concurrency import run_in_threadpool
    return await run_in_threadpool(validate_bytes,data,mime)


def validate_bytes(data,mime):
    if not data:
        raise HTTPException(400,'The selected file is empty.')
    if mime in IMAGE_TYPES:
        try:
            with warnings.catch_warnings():
                warnings.simplefilter('error',Image.DecompressionBombWarning)
                with Image.open(io.BytesIO(data)) as image:
                    if image.format!=IMAGE_TYPES[mime] or image.width*image.height>40_000_000:
                        raise ValueError('Unsupported image')
                    image.verify()
                with Image.open(io.BytesIO(data)) as image:
                    if getattr(image,'n_frames',1)>500 or getattr(image,'n_frames',1)*image.width*image.height>100_000_000:
                        raise ValueError('Too many frames')
                    for frame in range(getattr(image,'n_frames',1)):
                        image.seek(frame); image.load()
        except (UnidentifiedImageError, OSError, ValueError, Image.DecompressionBombError, Image.DecompressionBombWarning):
            raise HTTPException(400,'This image could not be decoded safely. Export it as a JPEG or PNG and retry.')
    else:
        valid=(data.startswith(b'\x1a\x45\xdf\xa3') if mime=='video/webm' else data[4:8] in ({b'ftyp',b'moov',b'mdat',b'wide'} if mime=='video/quicktime' else {b'ftyp'}))
        if not valid: raise HTTPException(400,'Video content does not match the selected file type.')
        try:
            with av.open(io.BytesIO(data)) as container:
                if not container.streams.video:raise ValueError('No video stream')
                stream=container.streams.video[0]
                if not 0<stream.width*stream.height<=40_000_000:raise ValueError('Video dimensions')
                stream.thread_count=1
                next(container.decode(video=0))
        except (av.FFmpegError,ValueError,StopIteration,OverflowError):
            raise HTTPException(400,'This video could not be decoded. Export a valid MP4 and retry.')
    return data,mime
