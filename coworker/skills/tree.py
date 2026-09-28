"""Copy policy shared by bundled and uploaded skill trees."""

from pathlib import PurePath

# Runtime-generated Python bytecode is not a portable skill resource. Keep source,
# scripts, dependency manifests and assets; never mutate the source package.
def is_skill_cache(path: PurePath) -> bool:
    return "__pycache__" in path.parts or path.suffix in {".pyc", ".pyo"}


def ignore_skill_cache(directory: str, names: list[str]) -> set[str]:
    return {name for name in names if is_skill_cache(PurePath(name))}
