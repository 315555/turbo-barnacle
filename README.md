"""批量整理作业文件：扫描、改名、归档、撤销。仅处理指定目录的第一层文件。"""

from __future__ import annotations

import argparse
import json
import os
import re
from datetime import datetime
from pathlib import Path


STATE_DIR = ".homework_manager"
JOURNAL = "last_operation.json"
SUPPORTED = {".pdf", ".docx"}
NAME_RULE = re.compile(r"^(?P<student>\d+)_(?P<name>[^_]+)_(?P<work>.+)$")


def files_in(folder: Path) -> list[Path]:
    """只查看当前目录；不跟随符号链接，也不碰子文件夹。"""
    return sorted(
        (p for p in folder.iterdir() if p.is_file() and not p.is_symlink()),
        key=lambda p: p.name.casefold(),
    )


def within(root: Path, path: Path) -> bool:
    return path.resolve(strict=False).is_relative_to(root)


def clean_segment(value: str) -> str:
    """学期名只能是单个安全文件夹名。"""
    if value in {"", ".", ".."} or not re.fullmatch(r"[\w\-\u4e00-\u9fff]+", value):
        raise ValueError("学期只能包含汉字、字母、数字、下划线或短横线")
    return value


def state_path(root: Path) -> Path:
    return root / STATE_DIR / JOURNAL


def save_journal(root: Path, operation: str, changes: list[tuple[Path, Path]]) -> None:
    state = root / STATE_DIR
    state.mkdir(exist_ok=True)
    data = {
        "operation": operation,
        "changes": [[str(src.relative_to(root)), str(dst.relative_to(root))] for src, dst in changes],
    }
    temporary = state / "last_operation.tmp"
    temporary.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    os.replace(temporary, state_path(root))


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
    # 先把旧操作记录换成空记录；每成功移动一个文件就立即更新。
    save_journal(root, "rename", completed)
    for source, target in planned:
        try:
            move_without_overwrite(source, target)
            completed.append((source, target))
            save_journal(root, "rename", completed)
        except OSError as exc:
            print(f"  跳过 {source.name}：{exc}")
    print(f"已改名 {len(completed)} 个文件。可运行 undo 撤销。")


def write_report(root: Path, semester: str, completed: list[tuple[Path, Path]], skipped: list[str]) -> Path:
    report_dir = root / STATE_DIR / "reports"
    report_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    report = report_dir / f"archive_{timestamp}.txt"
    lines = [f"学期：{semester}", f"处理：{len(completed)} 个", f"跳过：{len(skipped)} 个", "", "已归档："]
    lines += [f"{src.relative_to(root)} -> {dst.relative_to(root)}" for src, dst in completed]
    lines += ["", "跳过原因：", *skipped]
    report.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return report


def archive(root: Path, semester: str) -> None:
    semester = clean_segment(semester)
    planned: list[tuple[Path, Path]] = []
    skipped: list[str] = []
    for source in files_in(root):
        category = source.suffix.lower().lstrip(".") or "other"
        target = root / semester / category / source.name
        if not within(root, target) or not within(root, target.parent):
            skipped.append(f"{source.name}：目标目录指向指定文件夹之外")
        elif target.exists() or target.is_symlink():
            skipped.append(f"{source.name}：目标文件已存在")
        else:
            planned.append((source, target))

    print("归档预览：")
    for source, target in planned:
        print(f"  {source.name} -> {target.relative_to(root)}")
    for reason in skipped:
        print(f"  跳过 {reason}")
    if not planned or not confirm():
        print("未执行归档。")
        return
    completed: list[tuple[Path, Path]] = []
    save_journal(root, "archive", completed)
    for source, target in planned:
        try:
            target.parent.mkdir(parents=True, exist_ok=True)
            move_without_overwrite(source, target)
            completed.append((source, target))
            save_journal(root, "archive", completed)
        except OSError as exc:
            skipped.append(f"{source.name}：{exc}")
    report = write_report(root, semester, completed, skipped)
    print(f"已归档 {len(completed)} 个，跳过 {len(skipped)} 个；报告：{report}")
    print("可运行 undo 撤销归档；报告会保留作为记录。")


def undo(root: Path) -> None:
    journal = state_path(root)
    if not journal.exists():
        print("没有可撤销的操作。")
        return
    try:
        data = json.loads(journal.read_text(encoding="utf-8"))
        changes = data["changes"]
        if data["operation"] not in {"rename", "archive"} or not isinstance(changes, list):
            raise ValueError("记录格式错误")
        pairs = [(root / old, root / new) for old, new in changes]
        if any(not within(root, old) or not within(root, new) for old, new in pairs):
            raise ValueError("操作记录包含目录外的路径")
    except (OSError, ValueError, KeyError, TypeError) as exc:
        print(f"无法读取撤销记录：{exc}")
        return
    if not pairs:
        print("上次操作没有成功修改文件。")
        return
    print(f"撤销上次 {data['operation']}：")
    for old, new in reversed(pairs):
        print(f"  {new.relative_to(root)} -> {old.relative_to(root)}")
    if not confirm():
        print("未执行撤销。")
        return
    remaining = list(pairs)
    for old, new in reversed(pairs):
        if not new.is_file() or new.is_symlink() or old.exists() or old.is_symlink():
            print(f"  跳过 {new.relative_to(root)}：源文件丢失或原位置被占用")
            continue
        try:
            move_without_overwrite(new, old)
            remaining.remove((old, new))
            save_journal(root, data["operation"], remaining)
        except OSError as exc:
            print(f"  跳过 {new.relative_to(root)}：{exc}")
    print(f"已撤销 {len(pairs) - len(remaining)} 个，剩余 {len(remaining)} 个。")
    if not remaining:
        journal.unlink()


def main() -> None:
    parser = argparse.ArgumentParser(description="作业文件整理工具（只处理指定目录的第一层）")
    parser.add_argument("folder", type=Path, help="作业文件夹路径")
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("scan", help="列出文件").add_argument("--ext", help="按扩展名筛选，例如 pdf")
    commands.add_parser("rename", help="预览并批量改名")
    commands.add_parser("archive", help="按学期及文件扩展名分类归档").add_argument("--semester", required=True)
    commands.add_parser("undo", help="撤销上一次成功的改名或归档")
    args = parser.parse_args()
    root = args.folder.expanduser().resolve()
    if not root.is_dir():
        parser.error(f"文件夹不存在：{root}")
    if args.command == "scan":
        scan(root, args.ext)
    elif args.command == "rename":
        rename(root)
    elif args.command == "archive":
        try:
            archive(root, args.semester)
        except ValueError as exc:
            parser.error(str(exc))
    else:
        undo(root)


if __name__ == "__main__":
    main()
