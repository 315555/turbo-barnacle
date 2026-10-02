"""PDD 作业文件整理工具。只处理指定文件夹的第一层文件。"""

from __future__ import annotations

import argparse
from datetime import datetime
from pathlib import Path

def files_in(folder: Path) -> list[Path]:
    """只查看当前目录；不跟随符号链接，也不碰子文件夹。"""
    return sorted(
        (p for p in folder.iterdir() if p.is_file() and not p.is_symlink()),
        key=lambda p: p.name.casefold(),
    )


def scan(root: Path, extension: str | None) -> None:
    if extension and not extension.startswith("."):
        extension = "." + extension
    selected = [p for p in files_in(root) if extension is None or p.suffix.lower() == extension.lower()]
    if not selected:
        print("没有符合条件的文件。")
        return
    print(f"{'文件名':<42} {'大小(字节)':>12}  修改时间")
    for path in selected:
        stat = path.stat()
        print(f"{path.name:<42} {stat.st_size:>12}  {datetime.fromtimestamp(stat.st_mtime):%Y-%m-%d %H:%M:%S}")
    print(f"共 {len(selected)} 个文件")


def main() -> None:
    parser = argparse.ArgumentParser(description="作业文件整理工具")
    parser.add_argument("folder", type=Path, help="要处理的文件夹")
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("scan", help="扫描并列出文件").add_argument("--ext", help="扩展名，例如 pdf")
    args = parser.parse_args()
    root = args.folder.expanduser().resolve()
    if not root.is_dir():
        parser.error(f"文件夹不存在：{root}")
    scan(root, args.ext)


if __name__ == "__main__":
    main()
