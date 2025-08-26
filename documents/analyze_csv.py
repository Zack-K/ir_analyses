import pandas as pd
import chardet

file_path = 'C:/Users/NDY09/documents/ir_analyses/documents/test.csv'

with open(file_path, 'rb') as f:
    rawdata = f.read()
    encoding = chardet.detect(rawdata)['encoding']

df = pd.read_csv(file_path, encoding=encoding, delimiter='\t')

print('--- Columns ---')
print(df.columns)
print('--- Head ---')
print(df.head())
