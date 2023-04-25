import pandas as pd
import os
from tqdm import tqdm


def split_file(file_path, dest_dir, records_per_file, sheet_name=None):
    os.makedirs(dest_dir, exist_ok=True)
    if file_path.endswith('.xlsx') or file_path.endswith('.xls'):
        df = pd.read_excel(file_path, sheet_name=sheet_name)
        endfile = '.xlsx' if file_path.endswith('.xlsx') else '.xls'
        total_records = len(df)

        num_files = (total_records + records_per_file - 1) // records_per_file

        dfs = [df[i:i + records_per_file] for i in range(0, total_records, records_per_file)]

        for i in tqdm(range(num_files), desc="Đang chia nhỏ file"):
            file_name = f"file_{i + 1}.{endfile}"
            dest_file_path = os.path.join(dest_dir, file_name)
            dfs[i].to_excel(dest_file_path, index=False, sheet_name=sheet_name, engine='openpyxl')
        print(f'Tổng cộng đã chia {num_files} file.')

    elif file_path.endswith('.csv'):
        df = pd.read_csv(file_path)
        num_files = len(df) // records_per_file + 1 if records_per_file else 1
        for i in tqdm(range(num_files), desc='Đang chia file'):
            start = i * records_per_file
            end = min((i + 1) * records_per_file, len(df))
            if start < end:
                df_part = df.iloc[start:end]
                dest_file_path = os.path.join(dest_dir, f'part_{i + 1}.csv')
                df_part.to_csv(dest_file_path, index=False)
                num_files += 1
        print(f'Tổng cộng đã chia {num_files} file.')
    else:
        print("Định dạng file không được hỗ trợ!")


# Sử dụng
file_path = ''  # Đường dẫn của file đầu vào
dest_dir = ''  # Thư mục chứa các file nhỏ sau khi chia
sheet_name = 'Sample-spreadsheet-file'  # Sheet name trong trường hợp file đầu vào là exel
records_per_file = 100

if __name__ == '__main__':
    split_file(file_path, dest_dir, records_per_file, sheet_name)
