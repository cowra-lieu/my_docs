import html

def process_and_compare(input_file, out_file_3, out_file_1, report_html, field_names=None):
    """
    :param input_file: 原始输入文件路径
    :param out_file_3: 结尾为 \t3\tnull\tnull 的输出文件路径
    :param out_file_1: 结尾为 \t1\tnull\tnull 的输出文件路径
    :param report_html: 生成的 HTML 差异报告路径
    :param field_names: 自定义字段名称列表，例如 ['ID', 'Name', 'Price', 'Status']
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

    # 4. 比对两个文件并生成 HTML 报告
    max_rows = max(len(lines_3), len(lines_1))
    
    html_content = [
        '<!DOCTYPE html>',
        '<html>',
        '<head>',
        '<meta charset="utf-8">',
        '<title>数据比对报告</title>',
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
        '</style>',
        '</head>',
        '<body>',
        '<h2>逐行字段差异比对报告</h2>',
        f'<p><b>文件 1 (结尾 \\t3\\tnull\\tnull):</b> {out_file_3} (共 {len(lines_3)} 行)</p>',
        f'<p><b>文件 2 (结尾 \\t1\\tnull\\tnull):</b> {out_file_1} (共 {len(lines_1)} 行)</p>',
        '<table>',
        '  <thead>',
        '    <tr>',
        '      <th style="width: 50px;">行号</th>',
        '      <th style="width: 50%;">文件 1 内容</th>',
        '      <th style="width: 50%;">文件 2 内容</th>',
        '    </tr>',
        '  </thead>',
        '  <tbody>'
    ]

    for idx in range(max_rows):
        row_num = idx + 1
        line_a = lines_3[idx].rstrip('\r\n') if idx < len(lines_3) else None
        line_b = lines_1[idx].rstrip('\r\n') if idx < len(lines_1) else None

        if line_a is None:
            cell_a = '<span class="missing-row">[无对应行]</span>'
            cell_b = html.escape(line_b)
        elif line_b is None:
            cell_a = html.escape(line_a)
            cell_b = '<span class="missing-row">[无对应行]</span>'
        else:
            fields_a = line_a.split('@')
            fields_b = line_b.split('@')
            
            max_fields = max(len(fields_a), len(fields_b))
            rendered_a = []
            rendered_b = []

            for f_idx in range(max_fields):
                # 优先使用传入的自定义字段名，超出部分自动兜底为 Field X
                if f_idx < len(field_names) and field_names[f_idx]:
                    field_name = field_names[f_idx]
                else:
                    field_name = f"Field {f_idx + 1}"

                val_a = fields_a[f_idx] if f_idx < len(fields_a) else ""
                val_b = fields_b[f_idx] if f_idx < len(fields_b) else ""

                escaped_a = html.escape(val_a)
                escaped_b = html.escape(val_b)
                escaped_field_name = html.escape(field_name)

                # 判断字段是否不匹配
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

        html_content.append(f'    <tr>')
        html_content.append(f'      <td>{row_num}</td>')
        html_content.append(f'      <td>{cell_a}</td>')
        html_content.append(f'      <td>{cell_b}</td>')
        html_content.append(f'    </tr>')

    html_content.extend([
        '  </tbody>',
        '</table>',
        '</body>',
        '</html>'
    ])

    # 5. 保存 HTML 报告
    with open(report_html, 'w', encoding='utf-8') as f:
        f.write('\n'.join(html_content))

    print("处理完成！")
    print(f"- 文件 1 (3) 已保存至: {out_file_3}")
    print(f"- 文件 2 (1) 已保存至: {out_file_1}")
    print(f"- 比对报告已生成至: {report_html}")

# 使用示例
if __name__ == "__main__":
    # 在此处传入您的自定义字段名称列表
    my_fields = ["ID", "Name", "Category", "Price", "Stock", "Suffix_Info"]

    process_and_compare(
        input_file="input.txt",
        out_file_3="output_suffix_3.txt",
        out_file_1="output_suffix_1.txt",
        report_html="comparison_report.html",
        field_names=my_fields  # 传入字段名列表
    )
