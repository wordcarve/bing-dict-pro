import re # 导入正则表达式模块

def read_words_from_txt(file_path):
    """
    从TXT文件读取单词，一行一个，只保留纯英文字母的单词。
    """
    words = []
    with open(file_path, 'r', encoding='utf-8') as f:
        for line in f:
            word = line.strip() # 移除行首尾的空白字符
            # 检查单词是否只包含英文字母
            if re.fullmatch(r'[a-zA-Z]+', word):
                words.append(word)
    return words

# 以下是你的原始代码，保持不变
import json
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
import time
from bing import fetch_bing_dictionary # 确保这里导入的是修改后的 bing.py

def fetch_word(word, max_retries=5, initial_delay=1):
    """
    查询单个单词，如果 fetch_bing_dictionary 抛出异常，则会重试。
    :param word: 要查询的单词。
    :param max_retries: 最大重试次数。
    :param initial_delay: 初始重试延迟（秒）。
    """
    retries = 0
    while retries < max_retries:
        try:
            data = fetch_bing_dictionary(word)
            # 如果 fetch_bing_dictionary 成功返回数据，则认为成功
            return {word: data}
        except Exception as e: # 捕获所有可能来自 fetch_bing_dictionary 的异常
            if 'definitions' in str(e):
                return {word: None}  # 如果是定义未找到的异常，直接返回 None
            print(f"查询单词 '{word}' 失败: {e}，正在重试 ({retries + 1}/{max_retries})...")
            retries += 1
            time.sleep(initial_delay * (2 ** (retries - 1))) # 指数退避重试
    
    print(f"查询单词 '{word}' 失败，已达到最大重试次数。")
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

def batch_fetch_dictionary_multithread(input_file_path, output_json_path, max_workers=8):
    """
    多线程批量查询单词并实时写入JSON文件（始终闭合数组）。
    """
    words = read_words_from_txt(input_file_path) # 调用新的读取函数
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
                print(f"处理单词 '{word}' 的结果时发生异常: {exc}")
    print(f"所有查询已完成，结果已实时保存到 {output_json_path}")

if __name__ == "__main__":
    input_txt = 'coca60000.txt' # 将输入文件改为.txt
    output_json = 'dictionary.json'
    batch_fetch_dictionary_multithread(input_txt, output_json, max_workers=32)