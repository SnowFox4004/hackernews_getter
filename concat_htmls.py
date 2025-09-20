def html_files_to_pdf(html_files, output_pdf, paper_size="A4"):
    import os
    from weasyprint import HTML, CSS
    from weasyprint.text.fonts import FontConfiguration

    """
    将多个HTML文件合并为一个PDF文件，每个HTML文件从新页面开始

    Args:
        html_files: HTML文件路径列表
        output_pdf: 输出PDF文件路径
        paper_size: 纸张大小，如'A4', 'Letter', 'Legal'等
    """
    # 创建字体配置
    html_files.sort()
    html_files.reverse()
    font_config = FontConfiguration()

    # # 定义基础CSS样式，确保每个HTML从新页面开始
    # base_css = CSS(
    #     string=f"""
    #     @page {{
    #         size: {paper_size};
    #         margin: 1in;
    #     }}
    #     .new-page {{
    #         page-break-before: always;
    #     }}
    # """,
    #     font_config=font_config,
    # )

    # 自定义边距和方向
    base_css = CSS(
        string=f"""
        @page {{
            size: {paper_size};
            margin: 0.1in;
            margin-header: 0.1in;
            margin-footer: 0.1in;
        }}
        @page :left {{
            margin-left: 0.1in;
            margin-right: 0.1in;
        }}
        @page :right {{
            margin-left: 0.1in;
            margin-right: 0.1in;
        }}
        .new-page {{
             page-break-before: always;
        }}
        .page-break {{
            page-break-before: always;
        }}
    """,
        font_config=font_config,
    )

    # 创建PDF文档
    all_docs = []
    for i, html_file in enumerate(html_files):
        if not os.path.exists(html_file):
            print(f"警告: 文件 {html_file} 不存在，跳过")
            continue

        print(f"处理文件: {html_file}")
        # 为每个HTML文件创建文档对象
        html = HTML(html_file)
        # 如果是第一个文档，不添加分页；其他文档添加分页
        if i > 0:
            # 添加分页样式
            specific_css = CSS(
                string="body { page-break-before: always; }", font_config=font_config
            )
            all_docs.append(
                html.render(
                    stylesheets=[base_css, specific_css], font_config=font_config
                )
            )
        else:
            all_docs.append(
                html.render(stylesheets=[base_css], font_config=font_config)
            )

    if not all_docs:
        print("错误: 没有有效的HTML文件可处理")
        return

    # 合并所有文档
    first_doc = all_docs[0]
    for doc in all_docs[1:]:
        first_doc.pages.extend(doc.pages)

    # 保存PDF
    first_doc.write_pdf(output_pdf)
    print(f"PDF已保存至: {output_pdf}")


if __name__ == "__main__":
    # 示例用法
    html_files = ["file1.html", "file2.html", "file3.html"]

    # 设置输出文件路径
    output_pdf = "output.pdf"

    # 设置纸张大小（可选：A4, Letter, Legal, A3等）
    paper_size = "B4"

    # 转换为PDF
    html_files_to_pdf(html_files, output_pdf, paper_size)
