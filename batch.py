import csv
import json
import time
from bing import fetch_bing_dictionary

def batch_fetch_dictionary_from_csv_realtime(csv_file_path, output_json_path, delay=1):
    """
    从 CSV 文件中批量读取单词并使用 fetch_bing_dictionary 进行查询，
    然后将每个单词的结果实时追加保存到 JSON 文件。

    Args:
        csv_file_path (str): 输入 CSV 文件的路径。
        output_json_path (str): 输出 JSON 文件的路径。
        delay (int): 每次查询之间的延迟时间（秒）。
    """
    # 首次打开文件，写入一个空的 JSON 数组开始
    with open(output_json_path, mode='w', encoding='utf-8') as outfile:
        outfile.write('[\n') # 写入 JSON 数组的起始符

    first_entry = True # 标记是否是第一个写入的条目

    with open(csv_file_path, mode='r', encoding='utf-8') as infile:
        reader = csv.DictReader(infile)
        for row in reader:
            word = row.get('word')
            if word and word[0].isdigit():
                print(f"跳过数字: {word}")
                continue
            if word:
                print(f"正在查询单词: {word}")
                data = fetch_bing_dictionary(word)
                
                # 实时写入 JSON 文件
                with open(output_json_path, mode='a', encoding='utf-8') as outfile: # 使用 'a' 模式追加写入
                    if not first_entry:
                        outfile.write(',\n') # 如果不是第一个条目，写入逗号和换行符
                    json.dump({word: data}, outfile, ensure_ascii=False, indent=2)
                    first_entry = False
                print(f"单词 '{word}' 的结果已写入 {output_json_path}")
                time.sleep(delay)

    # 所有单词处理完毕后，关闭 JSON 数组
    with open(output_json_path, mode='a', encoding='utf-8') as outfile:
        outfile.write('\n]') # 写入 JSON 数组的结束符
    
    print(f"所有查询已完成，结果已保存到 {output_json_path}")

if __name__ == "__main__":
    input_csv = 'protoWords.csv'
    output_json = 'dictionary.json'
    batch_fetch_dictionary_from_csv_realtime(input_csv, output_json, delay=0.1)