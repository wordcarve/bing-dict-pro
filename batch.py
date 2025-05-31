import csv
import json
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from bing import fetch_bing_dictionary

def read_words_from_csv(csv_file_path):
    """
    从CSV文件读取所有合法单词（非数字开头），返回单词列表。
    """
    words = []
    with open(csv_file_path, mode='r', encoding='utf-8') as infile:
        reader = csv.DictReader(infile)
        for row in reader:
            word = row.get('word')
            if word and not word[0].isdigit():
                words.append(word)
    return words

def fetch_word(word):
    """
    查询单个单词，返回 {word: data} 结构。
    """
    try:
        data = fetch_bing_dictionary(word)
        return {word: data}
    except Exception as e:
        print(f"查询单词 '{word}' 时出错: {e}")
        return {word: None}

def append_json_object_to_array(file_path, obj, lock):
    """
    线程安全地将一个对象追加到JSON数组文件中，始终保持文件为合法闭合的JSON数组。
    """
    with lock:
        try:
            with open(file_path, 'r+', encoding='utf-8') as f:
                f.seek(0, 2)
                filesize = f.tell()
                if filesize <= 2:  # 只包含 []
                    f.seek(1)
                    json.dump(obj, f, ensure_ascii=False, indent=2)
                    f.write(']')
                else:
                    f.seek(filesize - 1)
                    f.write(',\n')
                    json.dump(obj, f, ensure_ascii=False, indent=2)
                    f.write(']')
        except Exception as e:
            print(f"写入JSON文件时出错: {e}")

def batch_fetch_dictionary_multithread(csv_file_path, output_json_path, max_workers=8):
    """
    多线程批量查询单词并实时写入JSON文件（始终闭合数组）。
    """
    words = read_words_from_csv(csv_file_path)
    print(f"共需查询 {len(words)} 个单词...")
    # 初始化JSON文件为[]
    with open(output_json_path, 'w', encoding='utf-8') as f:
        f.write('[]')
    lock = threading.Lock()
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_word = {executor.submit(fetch_word, word): word for word in words}
        for future in as_completed(future_to_word):
            word = future_to_word[future]
            try:
                result = future.result()
                append_json_object_to_array(output_json_path, result, lock)
                print(f"单词 '{word}' 查询并写入完成.")
            except Exception as exc:
                print(f"单词 '{word}' 查询时发生异常: {exc}")
                append_json_object_to_array(output_json_path, {word: None}, lock)
    print(f"所有查询已完成，结果已实时保存到 {output_json_path}")

if __name__ == "__main__":
    input_csv = 'protoWords.csv'
    output_json = 'dictionary.json'
    batch_fetch_dictionary_multithread(input_csv, output_json, max_workers=16)