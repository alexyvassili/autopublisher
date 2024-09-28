import os

from autopublisher.utils.transliterate import (
    transliterate, replace_non_alphabetic_symbols
)


def format_jpeg_name(jpeg_name):
    jpeg_name = transliterate(jpeg_name)
    jpeg_name = replace_non_alphabetic_symbols(jpeg_name)
    return jpeg_name.lower()


def get_file_size_mb(file_name):
    size = os.path.getsize(file_name)
    if size:
        return size / 1024 / 1024


def get_files_for_extension(folder, ext):
    return [
        item for item in os.listdir(folder)
        if os.path.isfile(os.path.join(folder, item))
        and item.lower().endswith(ext)
    ]


def get_fullpath_files_for_extension(folder, ext):
    return [
        os.path.join(folder, item)
        for item in get_files_for_extension(folder, ext)
    ]
