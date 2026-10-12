import re
import zipfile

from datetime import date
from pathlib import Path

from docx import Document

#日常巡检文档生成
class inspectionDoc:
    def __init__(self,tmp_doc_path):
        self.tmp_doc_path = tmp_doc_path
        self.doc = Document(self.tmp_doc_path)
        self._image_replacements = []  # [(内部路径, 新bytes), ...]
    def replace_dates(self, target_date=None):
        """将文档中的日期替换为目标日期（默认今天）。

        支持两种格式：
          - "2026年5月21日" → "YYYY年M月D日"（表格中的巡检时间）
          - "2026年5月"      → "YYYY年M月"     （页脚的年月）

        Word 经常把日期拆成多个 run（如 "202"/"6"/"年"/"5"/"月"/"21"/"日"），
        本方法会先合并相邻 run 的文本，匹配后再用第一个 run 的格式重写，
        确保字体、字号、颜色等样式不变。
        """
        if target_date is None:
            target_date = date.today()

        self._replace_date_in_tables(target_date)
        self._replace_date_in_paragraphs(target_date)
        return self

    def _replace_date_in_tables(self, target_date):
        full_pattern = re.compile(r"\d{4}年\d{1,2}月\d{1,2}日")
        new_full = f"{target_date.year}年{target_date.month}月{target_date.day}日"

        for table in self.doc.tables:
            for row in table.rows:
                for cell in row.cells:
                    for para in cell.paragraphs:
                        self._rewrite_runs(para, full_pattern, new_full)

    def _replace_date_in_paragraphs(self, target_date):
        ym_pattern = re.compile(r"\d{4}年\d{1,2}月(?!\d+日)")
        new_ym = f"{target_date.year}年{target_date.month}月"

        for para in self.doc.paragraphs:
            self._rewrite_runs(para, ym_pattern, new_ym)

    @staticmethod
    def _rewrite_runs(para, pattern, new_text):
        """在段落中查找匹配 pattern 的连续 run 组，替换为新文本。

        策略：先将所有 run 文本拼接，找到匹配位置，
        再定位该位置跨越了哪些 run，保留第一个 run 的格式，
        清空其余 run，将新文本写入第一个 run。
        """
        runs = para.runs
        if not runs:
            return

        full_text = "".join(r.text for r in runs)
        match = pattern.search(full_text)
        if not match:
            return

        # 计算匹配区域跨越了哪些 run
        start, end = match.start(), match.end()
        run_ranges = []
        pos = 0
        for i, run in enumerate(runs):
            run_end = pos + len(run.text)
            if run_end <= start or pos >= end:
                pass  # 不在匹配区域内
            else:
                run_ranges.append(i)
            pos = run_end

        if not run_ranges:
            return

        first_run_idx = run_ranges[0]
        first_run = runs[first_run_idx]

        # 计算第一个 run 中匹配前的保留文本
        pos = 0
        prefix = ""
        for i in range(first_run_idx):
            pos += len(runs[i].text)
        prefix = runs[first_run_idx].text[: max(0, start - pos)]

        # 清空匹配区域内的所有 run，将新文本写入第一个 run
        for idx in run_ranges:
            runs[idx].text = ""
        first_run.text = prefix + new_text
    def replace_image(self, internal_path, new_image_bytes):
        """替换 docx 内部指定路径的图片。
        Args:
            internal_path: docx 内部图片路径，如 "word/media/image1.png"。
                           可通过 list_images() 查看所有可用路径。
            new_image_bytes: 新图片的 bytes 数据。
        """
        self._image_replacements.append((internal_path, new_image_bytes))
        return self

    def list_images(self):
        """列出文档中所有图片的内部路径和大小，用于确认要替换哪张。"""
        with zipfile.ZipFile(str(self.tmp_doc_path), "r") as zf:
            images = sorted(
                [(n, zf.getinfo(n).file_size) for n in zf.namelist()
                 if n.startswith("word/media/") and not n.endswith("/")]
            )
        return images
    def save(self, output_path):
        """保存文档。如果替换了图片，通过 zipfile 层面确保图片字节被更新。"""
        output_path = Path(output_path)

        # 先用 python-docx 保存到临时文件（日期替换已生效）
        import tempfile
        tmp = Path(tempfile.mktemp(suffix=".docx"))
        self.doc.save(str(tmp))

        # 再用 zipfile 替换图片（最可靠，不依赖 python-docx 序列化）
        if self._image_replacements:
            self._replace_images_in_zip(tmp, output_path)
            tmp.unlink(missing_ok=True)
        else:
            tmp.replace(output_path)

    def _replace_images_in_zip(self, src_path, dst_path):
        """在 zip 层面替换图片字节，src 和 dst 可以是不同文件。"""
        replacements = dict(self._image_replacements)

        with zipfile.ZipFile(str(src_path), "r") as zin:
            with zipfile.ZipFile(str(dst_path), "w", zipfile.ZIP_DEFLATED) as zout:
                for item in zin.infolist():
                    if item.filename in replacements:
                        zout.writestr(item, replacements[item.filename])
                    else:
                        zout.writestr(item, zin.read(item.filename))