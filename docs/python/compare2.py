import difflib
import html

def process_and_compare_smart(input_file, out_file_3, out_file_1, report_html, field_names=None):
    """
    智能对齐比对脚本：利用 LCS / SequenceMatcher 自动匹配最接近的行，而非机械硬套行号
    """
    if field_names is None:
        field_names = []

    lines_3 = []
    lines_1 = []

    # 1. 读取原文件并按结尾拆分
    with open(input_file, 'r', encoding='utf-8') as f:
        for line in f:
            stripped_line = line.rstrip('\r\n')
            if stripped_line.endswith('\t3\tnull\tnull'):
                lines_3.append(line)
            elif stripped_line.endswith('\t1\tnull\tnull'):
                lines_1.append(line)

    # 2. 按字符串升序排序
    lines_3.sort()
    lines_1.sort()

    # 3. 写入拆分后的 2 个文件
    with open(out_file_3, 'w', encoding='utf-8') as f:
        f.writelines(lines_3)

    with open(out_file_1, 'w', encoding='utf-8') as f:
        f.writelines(lines_1)

    # 预处理：去掉换行符供比对
    clean_3 = [line.rstrip('\r\n') for line in lines_3]
    clean_1 = [line.rstrip('\r\n') for line in lines_1]

    # 4. 使用 difflib 计算最优化行对齐关系 (Diff Alignment)
    matcher = difflib.SequenceMatcher(None, clean_3, clean_1)
    
    # 构造对齐后的行对 (aligned_pairs)
    # 形式为: (line_a, line_b, index_a, index_b)
    aligned_pairs = []
    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag == 'equal': # 完全相同的块，逐行一对一匹配
            for offset in range(i2 - i1):
                aligned_pairs.append((clean_3[i1 + offset], clean_1[j1 + offset], i1 + offset + 1, j1 + offset + 1))
        elif tag == 'replace': # 内容不一致但位置对应的块
            len_a = i2 - i1
            len_b = j2 - j1
            max_len = max(len_a, len_b)
            for offset in range(max_len):
                la = clean_3[i1 + offset] if offset < len_a else None
                lb = clean_1[j1 + offset] if offset < len_b else None
                idx_a = (i1 + offset + 1) if offset < len_a else None
                idx_b = (j1 + offset + 1) if offset < len_b else None
                aligned_pairs.append((la, lb, idx_a, idx_b))
        elif tag == 'delete': # 文件1有，文件2缺失
            for offset in range(i2 - i1):
                aligned_pairs.append((clean_3[i1 + offset], None, i1 + offset + 1, None))
        elif tag == 'insert': # 文件1缺失，文件2有
            for offset in range(j2 - j1):
                aligned_pairs.append((None, clean_1[j1 + offset], None, j1 + offset + 1))

    # 5. 生成 HTML 比对报告
    html_content = [
        '<!DOCTYPE html>',
        '<html>',
        '<head>',
        '<meta charset="utf-8">',
        '<title>数据智能比对报告</title>',
        '<style>',
        '  body { font-family: monospace; background-color: #f8f9fa; margin: 20px; }',
        '  h2 { font-family: sans-serif; color: #333; }',
        '  table { border-collapse: collapse; width: 100%; background: #fff; box-shadow: 0 1px 3px rgba(0,0,0,0.1); }',
        '  th, td { border: 1px solid #dee2e6; padding: 6px 10px; font-size: 13px; text-align: left; vertical-align: top; word-break: break-all; }',
        '  th { background-color: #e9ecef; position: sticky; top: 0; }',
        '  tr:nth-child(even) { background-color: #f8f9fa; }',
        '  .diff-field { background-color: #ffc107; color: #000; font-weight: bold; padding: 2px 4px; border-radius: 3px; cursor: help; }',
        '  .field { display: inline-block; padding: 2px 4px; border-radius: 3px; }',
        '  .field:hover { background-color: #e2e6ea; cursor: help; }',
        '  .field-sep { color: #adb5bd; margin: 0 2px; }',
        '  .missing-row { background-color: #ffeef0; color: #d73a49; font-style: italic; }',
        '  .line-num { color: #888; font-size: 11px; }',
        '</style>',
        '</head>',
        '<body>',
        '<h2>智能行对齐与字段差异报告</h2>',
        f'<p><b>文件 1 (结尾 \\t3\\tnull\\tnull):</b> {out_file_3} (共 {len(lines_3)} 行)</p>',
        f'<p><b>文件 2 (结尾 \\t1\\tnull\\tnull):</b> {out_file_1} (共 {len(lines_1)} 行)</p>',
        '<table>',
        '  <thead>',
        '    <tr>',
        '      <th style="width: 80px;">行号(F1/F2)</th>',
        '      <th style="width: 50%;">文件 1 内容</th>',
        '      <th style="width: 50%;">文件 2 内容</th>',
        '    </tr>',
        '  </thead>',
        '  <tbody>'
    ]

    for line_a, line_b, idx_a, idx_b in aligned_pairs:
        str_idx_a = str(idx_a) if idx_a is not None else "-"
        str_idx_b = str(idx_b) if idx_b is not None else "-"
        row_label = f'<span class="line-num">L{str_idx_a} / L{str_idx_b}</span>'

        if line_a is None:
            cell_a = '<span class="missing-row">[缺失对应行]</span>'
            cell_b = html.escape(line_b)
        elif line_b is None:
            cell_a = html.escape(line_a)
            cell_b = '<span class="missing-row">[缺失对应行]</span>'
        else:
            fields_a = line_a.split('@')
            fields_b = line_b.split('@')
            
            max_fields = max(len(fields_a), len(fields_b))
            rendered_a = []
            rendered_b = []

            for f_idx in range(max_fields):
                field_name = field_names[f_idx] if f_idx < len(field_names) and field_names[f_idx] else f"Field {f_idx + 1}"
                val_a = fields_a[f_idx] if f_idx < len(fields_a) else ""
                val_b = fields_b[f_idx] if f_idx < len(fields_b) else ""

                escaped_a = html.escape(val_a)
                escaped_b = html.escape(val_b)
                escaped_field_name = html.escape(field_name)

                if val_a != val_b:
                    title_attr = f'title="字段: {escaped_field_name}&#10;不同: \'{escaped_a}\' vs \'{escaped_b}\'"'
                    rendered_a.append(f'<span class="diff-field" {title_attr}>{escaped_a}</span>')
                    rendered_b.append(f'<span class="diff-field" {title_attr}>{escaped_b}</span>')
                else:
                    title_attr = f'title="字段: {escaped_field_name}"'
                    rendered_a.append(f'<span class="field" {title_attr}>{escaped_a}</span>')
                    rendered_b.append(f'<span class="field" {title_attr}>{escaped_b}</span>')

            cell_a = '<span class="field-sep">@</span>'.join(rendered_a)
            cell_b = '<span class="field-sep">@</span>'.join(rendered_b)

        html_content.append('    <tr>')
        html_content.append(f'      <td>{row_label}</td>')
        html_content.append(f'      <td>{cell_a}</td>')
        html_content.append(f'      <td>{cell_b}</td>')
        html_content.append('    </tr>')

    html_content.extend([
        '  </tbody>',
        '</table>',
        '</body>',
        '</html>'
    ])

    with open(report_html, 'w', encoding='utf-8') as f:
        f.write('\n'.join(html_content))

    print("比对完成，已生成智能对齐报告！")

# 测试运行
if __name__ == "__main__":
    process_and_compare_smart(
        input_file="input.txt",
        out_file_3="output_suffix_3.txt",
        out_file_1="output_suffix_1.txt",
        report_html="comparison_report.html",
        field_names=["ID", "Value"]
    )
