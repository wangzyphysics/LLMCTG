"""Export the generated manual and current source tree as Markdown deliverables."""

from __future__ import annotations

from pathlib import Path

from docx import Document
from docx.document import Document as DocumentObject
from docx.oxml.table import CT_Tbl
from docx.oxml.text.paragraph import CT_P
from docx.table import Table
from docx.text.paragraph import Paragraph

from build_copyright_docs import DELIVERY, SOFTWARE_NAME, VERSION, source_files

ROOT = Path(__file__).resolve().parents[1]


def iter_blocks(parent):
    parent_element = parent.element.body if isinstance(parent, DocumentObject) else parent._tc
    for child in parent_element.iterchildren():
        if isinstance(child, CT_P):
            yield Paragraph(child, parent)
        elif isinstance(child, CT_Tbl):
            yield Table(child, parent)


def escape_cell(text: str) -> str:
    return "<br>".join(part.strip() for part in text.splitlines()).replace("|", "\\|")


def paragraph_is_code(paragraph: Paragraph) -> bool:
    visible_runs = [run for run in paragraph.runs if run.text]
    return bool(visible_runs) and all(run.font.name == "Consolas" for run in visible_runs)


def manual_to_markdown(source: Path, target: Path) -> None:
    document = Document(source)
    output: list[str] = []
    code_lines: list[str] = []

    def flush_code() -> None:
        if code_lines:
            output.extend(["```bash", *code_lines, "```", ""])
            code_lines.clear()

    for block in iter_blocks(document):
        if isinstance(block, Paragraph):
            text = block.text.strip()
            if not text:
                flush_code()
                continue
            if paragraph_is_code(block):
                code_lines.append(block.text)
                continue
            flush_code()
            style = block.style.name if block.style else ""
            if style == "Title":
                output.extend([f"# {text}", ""])
            elif style.startswith("Heading "):
                level = int(style.rsplit(" ", 1)[1])
                output.extend([f"{'#' * (level + 1)} {text}", ""])
            elif style.startswith("List Bullet"):
                output.extend([f"- {text}", ""])
            else:
                output.extend([text, ""])
        else:
            flush_code()
            rows = [[escape_cell(cell.text) for cell in row.cells] for row in block.rows]
            if not rows:
                continue
            output.append("| " + " | ".join(rows[0]) + " |")
            output.append("| " + " | ".join("---" for _ in rows[0]) + " |")
            for row in rows[1:]:
                output.append("| " + " | ".join(row) + " |")
            output.append("")
    flush_code()
    target.write_text("\n".join(output).rstrip() + "\n", encoding="utf-8")


def source_to_markdown(target: Path) -> None:
    files = source_files()
    total_lines = 0
    sections: list[str] = [
        f"# {SOFTWARE_NAME}{VERSION}源程序鉴别材料",
        "",
        "本文档收录当前 LLMCTG 目录中的核心程序、命令脚本、配置和自动化测试源码。",
        "生成文档的构建脚本不纳入鉴别材料。",
        "",
        "## 文件清单",
        "",
    ]
    for path in files:
        relative = path.relative_to(ROOT).as_posix()
        sections.append(f"- `{relative}`")
    for path in files:
        relative = path.relative_to(ROOT).as_posix()
        content = path.read_text(encoding="utf-8-sig").replace("\r\n", "\n").replace("\r", "\n")
        lines = content.splitlines()
        total_lines += len(lines)
        language = {
            ".py": "python", ".ps1": "powershell", ".sh": "bash",
            ".toml": "toml", ".json": "json",
        }.get(path.suffix.lower(), "text")
        sections.extend([
            "",
            f"## {relative}",
            "",
            f"```{language}",
            content.rstrip(),
            "```",
        ])
    sections[4:4] = [f"共收录 {len(files)} 个文件，约 {total_lines} 行源代码。", ""]
    target.write_text("\n".join(sections).rstrip() + "\n", encoding="utf-8")


def main() -> None:
    DELIVERY.mkdir(parents=True, exist_ok=True)
    manual_docx = DELIVERY / f"{SOFTWARE_NAME}{VERSION}用户操作手册.docx"
    manual_md = DELIVERY / f"{SOFTWARE_NAME}{VERSION}用户操作手册.md"
    source_md = DELIVERY / f"{SOFTWARE_NAME}{VERSION}源程序鉴别材料.md"
    manual_to_markdown(manual_docx, manual_md)
    source_to_markdown(source_md)
    print(manual_md)
    print(source_md)


if __name__ == "__main__":
    main()
