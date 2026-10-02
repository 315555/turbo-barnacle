# PDD 作业文件整理工具

用 Python 标准库完成扫描、批量改名、归档报告和撤销。无需安装第三方依赖；需要 Python 3.9 或更高版本。程序只处理指定文件夹**第一层**的文件，不会递归处理子目录。

## 从零运行

1. 将本项目解压，在终端进入 `pdd_homework` 文件夹。
2. 准备一个测试目录，如 `demo`，放入 `2026001_张三_高数作业.pdf` 和 `2026002_李四_英语作业.docx`。建议先用测试文件练习。
3. 根据自己的系统，把下列命令中的 `python` 换为 `python3`（若需要）。

```bash
python homework.py demo scan
python homework.py demo scan --ext pdf
python homework.py demo rename
python homework.py demo archive --semester 2026秋
python homework.py demo undo
python -m unittest -v
```

`demo` 是要处理的文件夹，可以换成绝对路径。`scan` 列出文件名、大小（字节）、修改时间；`--ext` 按扩展名筛选。`rename` 只改符合 `学号_姓名_作业名.pdf/docx` 的文件，例如 `2026001_张三_高数作业.pdf` 改成 `高数作业_2026001.pdf`。它先打印计划，只有输入 `y` 才会执行。格式不符和目标重名都会跳过。

`archive --semester 2026秋` 将当前目录的 PDF 放进 `2026秋/pdf/`，DOCX 放进 `2026秋/docx/`，其他扩展名放进相应扩展名文件夹，无扩展名放进 `other/`。它也会先预览和确认。报告保存在 `demo/.homework_manager/reports/`，包含处理数量、跳过数量和原因（例如目标重名）。`undo` 撤销上一次改名或归档：先预览确认；如果原位置被占用，会跳过，保留尚未撤销的记录供下次重试。归档报告作为历史记录保留。

每次成功执行新的改名或归档，会替换“上次操作”的撤销记录，因此要撤销时请在下一次改动前运行 `undo`。文件移动只在同一目录树内进行；如果存储设备不支持硬链接，程序会跳过并报告错误，不会覆盖目标文件。不要在执行程序的同时手动修改这些文件。

## 对应考题的三个 PR

- PR 1：扫描与列出。核心是 `files_in()`、`scan()`，学会 `Path`、循环和筛选。
- PR 2：批量改名。核心是 `rename()`、`confirm()`、`move_without_overwrite()`，学会正则、预览与重名检查。
- PR 3：归档与报告。核心是 `archive()`、`write_report()`、`undo()`、`save_journal()`，学会操作记录和撤销。

这份代码是可运行的完整版本。考核需要**三个独立的 GitHub PR**，下载代码本身不会自动生成 PR；提交时应按部门给出的仓库规则拆分，并能解释每次改动。推荐自己先运行、逐个理解函数，再把三个需求分次提交。
