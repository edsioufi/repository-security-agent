"""
Small, framework-independent snapshot and access boundary for source review.
"""

import os
import stat
from pathlib import Path

EXCLUDED = {
    "node_modules",
    "vendor",
    "dist",
    "build",
    "__pycache__",
    "venv",
    "env",
    "coverage",
    "recordings",
    "secrets",
    "credentials",
    "target",
    "logs",
    "package-lock.json",
    "uv.lock",
}
EXTENSIONS = {
    ".py",
    ".js",
    ".ts",
    ".tsx",
    ".jsx",
    ".html",
    ".css",
    ".sql",
    ".md",
    ".txt",
    ".toml",
    ".yaml",
    ".yml",
    ".json",
    ".sh",
}
MAX_FILE = 64_000
MAX_TOTAL = 1_000_000
MAX_RESULT = 6000


class Source:
    def __init__(self, root):
        root = Path(root).expanduser().resolve(strict=True)
        if not root.is_dir():
            raise ValueError("Choose a repository directory")
        self.files = {}
        self.omitted = 0
        total = 0
        for directory, dirs, names, directory_fd in os.fwalk(
            root, follow_symlinks=False
        ):
            dirs[:] = sorted(
                d
                for d in dirs
                if not d.startswith(".")
                and d.lower() not in EXCLUDED
                and not (Path(directory) / d).is_symlink()
            )
            for name in sorted(names):
                source = Path(directory) / name
                low = name.lower()
                if (
                    not stat.S_ISREG(source.lstat().st_mode)
                    or source.is_symlink()
                    or name.startswith(".")
                    or low in EXCLUDED
                    or any(
                        s in low
                        for s in (
                            "secret",
                            "credential",
                            "api_key",
                            "private",
                            ".env",
                            "password",
                            "token",
                        )
                    )
                    or low in {"key.txt", "keys.json", "id_rsa", "id_ed25519"}
                    or source.suffix.lower() not in EXTENSIONS
                    or source.stat().st_size > MAX_FILE
                ):
                    self.omitted += 1
                    continue
                # O_NOFOLLOW also rejects a final-component symlink swapped
                # during selection.
                fd = os.open(
                    name,
                    os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK,
                    dir_fd=directory_fd,
                )
                with os.fdopen(fd, "rb") as stream:
                    if not stat.S_ISREG(os.fstat(stream.fileno()).st_mode):
                        self.omitted += 1
                        continue
                    raw = stream.read(MAX_FILE + 1)
                if (
                    len(raw) > MAX_FILE
                    or b"\0" in raw
                    or total + len(raw) > MAX_TOTAL
                    or len(self.files) >= 500
                ):
                    self.omitted += 1
                    continue
                try:
                    content = raw.decode("utf-8")
                except UnicodeDecodeError:
                    self.omitted += 1
                    continue
                # Defense in depth for common inline credentials; selection is
                # not a DLP guarantee.
                if any(
                    marker in content
                    for marker in (
                        "AIza",
                        "-----BEGIN PRIVATE KEY",
                        "ghp_",
                        "sk-proj-",
                    )
                ):
                    self.omitted += 1
                    continue
                path = source.relative_to(root).as_posix()
                self.files[path] = content
                total += len(raw)

    def lines(self, path):
        if (
            not isinstance(path, str)
            or path not in self.files
            or ".." in Path(path).parts
            or Path(path).is_absolute()
        ):
            raise ValueError(
                "Use an exact relative path returned by list_files; excluded "
                "or outside paths are unavailable"
            )
        return self.files[path].splitlines()

