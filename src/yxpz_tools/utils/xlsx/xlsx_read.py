import os
from datetime import datetime
import binascii
import xlrd
from openpyxl import load_workbook

def get_all_sheetNames(file_path):
    if not os.path.exists(file_path):
        raise Exception(f'{file_path} 文件不存在')
    workbook = load_workbook(file_path)
    sheet_names = workbook.sheetnames
    workbook.close()
    return sheet_names

def detect_excel_format(file_path):
    with open(file_path, 'rb') as f:
        header = binascii.hexlify(f.read(8)).decode('utf-8').upper()
    if header.startswith('D0CF11E0A1B11AE1'):
        return '.xls'
    elif header.startswith('504B0304'):
        return '.xlsx'
    else:
        raise ValueError("Not a valid Excel file")

def read_all_excel(file_path):
    data_line = None
    if file_path.endswith('.xls'):
        data_line = readXls(file_path)
    elif file_path.endswith('.xlsx'):
        data_line = excelRead(file_path)
    else:
        raise ValueError("其他文件类型")
    return data_line

def read_all_type_excel(file_path):

    read_type = detect_excel_format(file_path)
    file_type = file_path[file_path.rfind('.'):]
    is_rename = False
    before_name = None
    if not read_type == file_type:
        end_type = read_type
        print(f'\n{os.path.basename(file_path)}:文件后缀类型和文件内容判断的类型不相等，'
              f'程序默认使用实际类型,并修改文件后缀名称,现在文件名称为：{os.path.basename(file_path).replace(file_type, end_type)}')
        new_file_path = file_path.replace(file_type, end_type)
        os.rename(file_path, new_file_path)
        before_name = file_path
        file_path = new_file_path

    data_line = read_all_excel(file_path)
    if is_rename: #如果修改名称后还是无法读取，需要回滚到之前的状态
        # print('文件修改后缀依旧无法读取，进行回滚操作')
        os.rename(file_path, before_name)
    elif data_line is None:
        raise Exception(f'文件读取失败: {file_path}')
    return data_line
def read_all_type_excel_by_column(file_path):
    all_column_data = None
    if file_path.endswith('.xls'):
        all_column_data = readXlsByColumn(file_path)
    elif file_path.endswith('.xlsx'):
        all_column_data = excelReadByColumn(file_path)
    return all_column_data
#获取所有数据，用二维数组保存
def excelRead(filename,sheet_name = None):
    all_data = []
    workbook = load_workbook(filename)
    # worksheet = workbook['Sheet1']
    if sheet_name == None:
        worksheet = workbook.active
    else:
        worksheet = workbook[sheet_name]
    rows = worksheet.rows
    for row in rows:
        data = []
        for col in row:
            data.append(col.value)
        all_data.append(data)
    workbook.close()
    return all_data
def excelReadByColumn(filename):
    # 加载 Excel 文件
    workbook = load_workbook(filename)  # 替换为你的文件名
    sheet = workbook.active  # 获取当前活动的工作表
    all_col_data = []
    # 逐列读取数据
    for col in sheet.iter_cols(values_only=True):  # values_only=True 只获取值，不包含单元格对象
        column_data = list(col)  # 将列数据转换为列表
        if column_data[0] ==None:
            continue
        # print(column_data)  # 打印当前列的数据
        all_col_data.append(column_data)
    # print(f'filename={filename}')
    # for row in all_col_data:
    #     print(row)
    return all_col_data

    # for col in sheet.iter_cols(min_col=2, max_col=3, values_only=True):  # 只读取第2列和第3列
    #     print(list(col))

def excelReadLine(file_name,row_num):
    wb = load_workbook(file_name)
    wa = wb.active
    row = row_num
    line_content = []
    print(len(wa.max_column))
    return line_content

def readXls(file_name):
    all_data = []
    wb = xlrd.open_workbook(file_name)
    st = wb.sheet_by_index(0)
    for row in range(st.nrows):
        data = []
        for col in range(st.ncols):
            cell_value = st.cell_value(row, col)
            cell_type = st.cell_type(row, col)
            if cell_type == xlrd.XL_CELL_DATE:
                # print(f'{cell_type = },{cell_value = }')
                try:
                    dt = datetime(*xlrd.xldate_as_tuple(cell_value, wb.datemode))
                    if cell_value < 1: #纯时间
                        data.append(dt.strftime('%H:%M:%S'))
                    else:
                        data.append(dt.strftime('%Y-%m-%d %H:%M:%S'))
                except Exception as e:
                    print('日期转换异常')
                    data.append(cell_value)
            else:
                data.append(cell_value)
        all_data.append(data)
    return all_data

def readXlsByColumn(filename):
    all_columns = []

    # 打开 .xls 文件
    workbook = xlrd.open_workbook(filename)  # 替换为你的文件名
    sheet = workbook.sheet_by_index(0)  # 获取第一个工作表
    for col_index in range(sheet.ncols):  # 遍历每一列
        column_data = []  # 用于存储列数据
        for row_index in range(sheet.nrows):  # 遍历每一行
            column_data.append(sheet.cell_value(row_index, col_index))  # 获取指定列的值
        all_columns.append(column_data)
    return all_columns

def excelReadCell(file_name,row_num,col_num):
    wb = load_workbook(file_name)
    wa = wb.active
    cell = wa.cell(row=row_num,column=col_num)
    return cell.value

def get_excel_all_sheets(file_path):
    wb = load_workbook(file_path)
    sheets = wb.sheetnames
    return sheets

