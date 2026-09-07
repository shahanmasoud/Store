from __future__ import annotations

import io
import warnings
from pathlib import Path
from uuid import uuid4

from fastapi import HTTPException, status
from PIL import Image, ImageOps, UnidentifiedImageError
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models.catalog import Product

ALLOWED_CONTENT_TYPES = {"image/jpeg", "image/png", "image/webp"}
FORMAT_EXTENSION = {"JPEG": ".jpg", "PNG": ".png", "WEBP": ".webp"}
FORMAT_CONTENT_TYPE = {"JPEG": "image/jpeg", "PNG": "image/png", "WEBP": "image/webp"}
MAX_IMAGE_PIXELS = 40_000_000
MAX_IMAGE_SIDE = 12_000


def _active_product(db: Session, product_id: int) -> Product:
    product = db.get(Product, product_id)
    if product is None or not product.is_active:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="کالای فعال پیدا نشد.")
    return product


def _product_directory() -> Path:
    root = get_settings().media_root.expanduser().resolve()
    directory = (root / "products").resolve()
    if root not in directory.parents:
        raise RuntimeError("مسیر رسانه نامعتبر است.")
    directory.mkdir(parents=True, exist_ok=True)
    return directory


def _safe_existing_path(filename: str | None) -> Path | None:
    if not filename:
        return None
    directory = _product_directory()
    candidate = (directory / filename).resolve()
    if candidate.parent != directory:
        return None
    return candidate


def _validated_and_sanitized_image(content: bytes, declared_content_type: str | None) -> tuple[bytes, str]:
    settings = get_settings()
    if declared_content_type not in ALLOWED_CONTENT_TYPES:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="فقط تصویر JPEG، PNG یا WebP قابل بارگذاری است.",
        )
    if not content:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="فایل تصویر خالی است.")
    if len(content) > settings.product_image_max_bytes:
        raise HTTPException(status_code=status.HTTP_413_CONTENT_TOO_LARGE, detail="حجم تصویر از حد مجاز بیشتر است.")

    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            with Image.open(io.BytesIO(content)) as probe:
                probe.verify()
            with Image.open(io.BytesIO(content)) as source:
                actual_format = source.format
                if actual_format not in FORMAT_EXTENSION:
                    raise HTTPException(
                        status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
                        detail="محتوای فایل باید تصویر JPEG، PNG یا WebP معتبر باشد.",
                    )
                if FORMAT_CONTENT_TYPE[actual_format] != declared_content_type:
                    raise HTTPException(
                        status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
                        detail="نوع اعلام‌شده فایل با محتوای واقعی تصویر یکسان نیست.",
                    )
                width, height = source.size
                if width <= 0 or height <= 0 or width > MAX_IMAGE_SIDE or height > MAX_IMAGE_SIDE or width * height > MAX_IMAGE_PIXELS:
                    raise HTTPException(
                        status_code=status.HTTP_413_CONTENT_TOO_LARGE,
                        detail="ابعاد تصویر از حد مجاز بیشتر است.",
                    )
                cleaned = ImageOps.exif_transpose(source)
                output = io.BytesIO()
                if actual_format == "JPEG":
                    if cleaned.mode not in {"RGB", "L"}:
                        cleaned = cleaned.convert("RGB")
                    cleaned.save(output, format="JPEG", quality=90, optimize=True)
                elif actual_format == "PNG":
                    cleaned.save(output, format="PNG", optimize=True)
                else:
                    cleaned.save(output, format="WEBP", quality=90, method=4)
    except HTTPException:
        raise
    except (UnidentifiedImageError, OSError, SyntaxError, Image.DecompressionBombError, Image.DecompressionBombWarning) as exc:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="محتوای فایل تصویر معتبر نیست.",
        ) from exc

    sanitized = output.getvalue()
    if len(sanitized) > settings.product_image_max_bytes:
        raise HTTPException(status_code=status.HTTP_413_CONTENT_TOO_LARGE, detail="حجم تصویر پردازش‌شده از حد مجاز بیشتر است.")
    return sanitized, FORMAT_EXTENSION[actual_format]


def replace_product_image(
    db: Session,
    *,
    product_id: int,
    content: bytes,
    content_type: str | None,
) -> Product:
    product = _active_product(db, product_id)
    sanitized, extension = _validated_and_sanitized_image(content, content_type)
    directory = _product_directory()
    filename = f"{uuid4().hex}{extension}"
    new_path = directory / filename
    old_path = _safe_existing_path(product.image_filename)

    try:
        with new_path.open("xb") as target:
            target.write(sanitized)
        product.image_filename = filename
        db.commit()
        db.refresh(product)
    except (OSError, SQLAlchemyError) as exc:
        db.rollback()
        new_path.unlink(missing_ok=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="ذخیره تصویر انجام نشد؛ تصویر قبلی بدون تغییر باقی ماند.",
        ) from exc

    if old_path is not None and old_path != new_path:
        try:
            old_path.unlink(missing_ok=True)
        except OSError:
            # The DB already points exclusively to the new randomized file. A
            # cleanup failure may leave an unreferenced file, but never loses
            # the newly committed image or re-exposes it through the catalog.
            pass
    return product


def remove_product_image(db: Session, *, product_id: int) -> Product:
    product = _active_product(db, product_id)
    old_path = _safe_existing_path(product.image_filename)
    quarantined_path: Path | None = None
    if old_path is not None and old_path.is_file():
        quarantined_path = old_path.with_name(f".deleting-{uuid4().hex}")
        try:
            old_path.replace(quarantined_path)
        except OSError as exc:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="حذف امن فایل تصویر انجام نشد؛ اطلاعات کالا تغییر نکرد.",
            ) from exc
    product.image_filename = None
    try:
        db.commit()
        db.refresh(product)
    except SQLAlchemyError as exc:
        db.rollback()
        if quarantined_path is not None:
            try:
                quarantined_path.replace(old_path)
            except OSError:
                pass
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="حذف تصویر ثبت نشد.",
        ) from exc
    if quarantined_path is not None:
        try:
            quarantined_path.unlink(missing_ok=True)
        except OSError:
            pass
    return product
