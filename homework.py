"""PDD 作业文件整理工具。只处理指定文件夹的第一层文件。"""

from __future__ import annotations

import argparse
import os
import re
from datetime import datetime
from pathlib import Path

SUPPORTED = {".pdf", ".docx"}
NAME_RULE = re.compile(r"^(?P<student>\d+)_(?P<name>[^_]+)_(?P<work>.+)$")


def files_in(folder: Path) -> list[Path]:
    """只查看当前目录；不跟随符号链接，也不碰子文件夹。"""
    return sorted(
        (p for p in folder.iterdir() if p.is_file() and not p.is_symlink()),
        key=lambda p: p.name.casefold(),
    )


def move_without_overwrite(source: Path, destination: Path) -> None:
    """目标存在时 os.link 会失败；成功后删除原路径，避免 rename 覆盖文件。"""
    os.link(source, destination)
    try:
        source.unlink()
    except OSError:
        destination.unlink()
        raise


def confirm() -> bool:
    try:
        return input("确认执行？输入 y 后回车：").strip().lower() == "y"
    except EOFError:
        return False


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


def rename(root: Path) -> None:
    planned: list[tuple[Path, Path]] = []
    skipped: list[str] = []
    originals = {p.name for p in files_in(root)}
    reserved: set[str] = set()
    for source in files_in(root):
        if source.suffix.lower() not in SUPPORTED:
            skipped.append(f"{source.name}：不是 PDF/DOCX")
            continue
        match = NAME_RULE.fullmatch(source.stem)
        if not match:
            skipped.append(f"{source.name}：不符合 学号_姓名_作业名 格式")
            continue
        target_name = f"{match['work']}_{match['student']}{source.suffix}"
        target = root / target_name
        if target_name == source.name:
            skipped.append(f"{source.name}：无需修改")
        elif target_name in originals or target_name in reserved:
            skipped.append(f"{source.name}：目标 {target_name} 已存在或重名")
        else:
            planned.append((source, target))
            reserved.add(target_name)

    print("改名预览：")
    for source, target in planned:
        print(f"  {source.name} -> {target.name}")
    for reason in skipped:
        print(f"  跳过 {reason}")
    if not planned or not confirm():
        print("未执行改名。")
        return
    completed: list[tuple[Path, Path]] = []
    for source, target in planned:
        try:
            move_without_overwrite(source, target)
            completed.append((source, target))
        except OSError as exc:
            print(f"  跳过 {source.name}：{exc}")
    print(f"已改名 {len(completed)} 个文件。")


def main() -> None:
    parser = argparse.ArgumentParser(description="作业文件整理工具")
    parser.add_argument("folder", type=Path, help="要处理的文件夹")
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("scan", help="扫描并列出文件").add_argument("--ext", help="扩展名，例如 pdf")
    commands.add_parser("rename", help="先预览，再批量改名")
    args = parser.parse_args()
    root = args.folder.expanduser().resolve()
    if not root.is_dir():
        parser.error(f"文件夹不存在：{root}")
    if args.command == "scan":
        scan(root, args.ext)
    else:
        rename(root)


if __name__ == "__main__":
    main()
