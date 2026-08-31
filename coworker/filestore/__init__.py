"""Platform-neutral FileRef / FileStorage (D-194).

Local session artifacts stay on disk. Cloud storage is only used when Channel
delivery (``send_file``) needs a cross-terminal URL or shared object.
"""

from __future__ import annotations

from .base import FileStorage, FileStorageError, NullFileStorage
from .config import FILESTORE_SECRET_PROFILE, CosConfig, load_cos_config, load_file_storage
from .memory import MemoryFileStorage
from .models import FileRef
from .tencent_cos import TencentCosStorage

__all__ = [
    "FILESTORE_SECRET_PROFILE",
    "CosConfig",
    "FileRef",
    "FileStorage",
    "FileStorageError",
    "MemoryFileStorage",
    "NullFileStorage",
    "TencentCosStorage",
    "load_cos_config",
    "load_file_storage",
]
