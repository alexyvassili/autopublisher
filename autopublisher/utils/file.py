from pathlib import Path

from autopublisher.utils.transliterate import (
    replace_non_alphabetic_symbols,
    transliterate,
)


def format_img_name(jpeg_name: str) -> str:
    jpeg_name = transliterate(jpeg_name)
    jpeg_name = replace_non_alphabetic_symbols(jpeg_name)
    return jpeg_name.lower()


def get_file_size_mb(file_name: Path) -> float:
    size = file_name.stat().st_size
    if size:
        return size / 1024 / 1024

    raise RuntimeError("Файл %r имеет нулевой размер", size)


def get_files_for_extension(
        folder: Path, ext: str,
) -> list[Path]:
    if not ext.startswith("."):
        ext = f".{ext}"
    ext = ext.lower()
    items = []
    for item in folder.iterdir():
        item_path = folder / item
        if item_path.is_file() and item_path.suffix.lower() == ext.lower():
            items.append(item)

    return items
