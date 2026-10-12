import os

from openpyxl.reader.excel import load_workbook
from openpyxl.styles import Font
from openpyxl.styles import PatternFill, Alignment
from openpyxl.utils import get_column_letter
from openpyxl.workbook import Workbook
from openpyxl.worksheet.hyperlink import Hyperlink


def writeAllLine(fileName, dataLines, sheet_name=None):
    ws = None
    if os.path.exists(fileName):
        workbook = load_workbook(fileName)
        if sheet_name:
            ws = workbook.create_sheet(sheet_name)
    else:
        workbook = Workbook()
        if sheet_name:
            ws = workbook.active
            ws.title = sheet_name
    if not sheet_name:
        ws = workbook.active

    for dataLine in dataLines:
        ws.append(dataLine)
    # ws['J'].number_format = 'General'
    workbook.save(fileName)


def writeAllLineByColumn(fileName, column_data):
    ws = None
    if os.path.exists(fileName):
        workbook = load_workbook(fileName)
    else:
        workbook = Workbook()
    ws = workbook.active

    # 将二维数组逐列写入 Excel
    for col_index, column in enumerate(column_data, start=1):  # 列索引从1开始
        for row_index, value in enumerate(column, start=1):  # 行索引从1开始
            ws.cell(row=row_index, column=col_index, value=value)  # 写入数据
    # 保存新 Excel 文件
    workbook.save(fileName)  # 替换为你想要保存的文件名


def copy_all_content_and_style(source_file, target_file):
    # 加载工作簿
    source_wb = load_workbook(source_file)
    if os.path.exists(target_file):
        target_wb = load_workbook(target_file)
    else:
        target_wb = Workbook()

    # 复制工作表
    source_sheet = source_wb.active
    target_sheet = target_wb.active  # 创建一个新工作表
    print(source_sheet.max_row)
    print(source_sheet.max_column)
    # 复制内容和格式
    for row in source_sheet.iter_rows():
        for cell in row:
            target_cell = target_sheet.cell(row=cell.row, column=cell.column)
            target_cell.value = cell.value
            target_cell.font = cell.font.copy()
            target_cell.border = cell.border.copy()
            target_cell.fill = cell.fill.copy()
            target_cell.alignment = cell.alignment.copy()

    # 复制行高和列宽
    for row in range(1, source_sheet.max_row + 1):
        target_sheet.row_dimensions[row].height = source_sheet.row_dimensions[row].height

    for col in range(1, source_sheet.max_column + 1):
        col_letter = source_sheet.cell(row=1, column=col).column_letter
        target_sheet.column_dimensions[col_letter].width = source_sheet.column_dimensions[col_letter].width

    # 删除空行
    rows_to_delete = []
    for row in target_sheet.iter_rows():
        # 检查整行是否为空
        if all(cell.value is None for cell in row):
            rows_to_delete.append(row[0].row)  # 记录空行的行号
    # 从下往上删除空行（避免行号错乱）
    print(f'rows_to_delete={rows_to_delete}')
    for row_idx in reversed(rows_to_delete):
        target_sheet.delete_rows(row_idx)

    # 保存目标文件
    target_wb.save(target_file)
    print(f"工作表已复制并保存到 {target_file}")


def write_data_to_new_sheet(fileName, dataLines, new_sheet_name='结果'):
    workbook = load_workbook(fileName)
    ws = workbook.create_sheet(title=new_sheet_name)
    for dataLine in dataLines:
        ws.append(dataLine)
    workbook.save(fileName)


def set_style_number():
    file_name = r'xx.xlsx'
    wb = load_workbook(file_name)
    ws = wb.active
    for cell in ws['L']:
        if not cell.value == None:
            cell.value = int(cell.value)
        # cell.style = NamedStyle(name='number_style',number_format='0')
        # ws['L'].style = NamedStyle(name='number_style',number_format='0')
    wb.save(file_name)


# set_style_number()

def set_yellow_color(file_name, row_num_line: list):
    wb = load_workbook(file_name)
    ws = wb.active
    fill = PatternFill(start_color='FFFF00', end_color='FFFF00', fill_type='solid')
    for row_num in row_num_line:
        for cell in ws[row_num]:
            cell.fill = fill
    wb.save(file_name)


def set_value(file_name, value, row_num, col_num):
    wb = load_workbook(file_name)
    ws = wb.active
    cell = ws[row_num][col_num]
    cell.value = value
    wb.save(file_name)


def kv_to_write(file_name, kv, sheet_name=None):
    def set_hyperlink(ws, row_num, last_col, url_name, url_value):
        file_line_cell = ws.cell(row=row_num, column=last_col, value=url_name)
        hyperlink = Hyperlink(ref=file_line_cell.coordinate,
                              target=url_value)
        file_line_cell.hyperlink = hyperlink
        file_line_cell.font = Font(color='0000FF', underline="single")

    if os.path.exists(file_name):
        os.remove(file_name)
    wb = Workbook()
    ws = wb.active

    ws.cell(row=1, column=1, value='业务组')
    ws.cell(row=1, column=2, value='版本')
    ws.cell(row=1, column=3, value='配置类型')
    ws.cell(row=1, column=4, value='内容')

    row1 = 2
    row2 = 2
    row3 = 2
    for k1, v1 in kv.items():
        ws.cell(row=row1, column=1, value=k1)
        row1_add = 0
        for k2, v2 in v1.items():
            row1_add += len(v2)
        ws.merge_cells(start_row=row1, start_column=1, end_row=row1 + row1_add - 1, end_column=1)
        row1 = row1_add + row1
        for k2, v2 in v1.items():
            ws.cell(row=row2, column=2, value=k2)
            row2_add = len(v2) - 1
            ws.merge_cells(start_row=row2, start_column=2, end_row=row2 + row2_add, end_column=2)
            row2 = row2_add + row2 + 1
            for k3, v3 in v2.items():
                ws.cell(row=row3, column=3, value=k3)
                # ws.cell(row=row3, column=4, value=v3)
                set_hyperlink(ws, row3, 5, '打开文件路径', 'file:///' + v3)
                row3 += 1

    # 设置单元格居中
    for row in ws.iter_rows():
        for cell in row:
            cell.alignment = Alignment(horizontal='center', vertical='center')
    ws.column_dimensions[get_column_letter(1)].width = 20
    ws.column_dimensions[get_column_letter(2)].width = 80
    ws.column_dimensions[get_column_letter(3)].width = 15
    ws.column_dimensions[get_column_letter(4)].width = 50
    ws.column_dimensions[get_column_letter(5)].width = 15
    ws.row_dimensions[1].height = 40
    for row in range(2, row3):
        ws.row_dimensions[row].height = 72
    wb.save(file_name)
