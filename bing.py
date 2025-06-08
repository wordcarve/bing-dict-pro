import requests
from bs4 import BeautifulSoup
import json
from urllib.parse import urlencode

def process_text_cleanup(text):
    """
    处理文本中的标点符号和全角斜杠。
    - 将中文全角斜杠“／”替换为英文斜杠“ / ”。
    - 移除英文标点符号前多余的空格。
    """
    if not isinstance(text, str):
        return ""
    text = text.replace('／', ' / ') # 替换全角斜杠
    # 移除标点符号前的多余空格
    # 例如 "word ." 变成 "word."
    text = text.replace(' .', '.').replace(' ,', ',').replace(' ?', '?').replace(' !', '!')
    text = text.replace(' :', ':').replace(' ;', ';')
    return text

def extract_examples(item_container):
    """
    从释义条目容器中提取例句。
    """
    examples = []
    exambar = item_container.find('div', class_='exambar')
    if not exambar:
        return examples
    
    for ex in exambar.find_all('div', class_='examlistitem'):
        en_ex = ex.find('div', class_='examitmeval')
        cn_ex = ex.find('div', class_='examitemname')
        if en_ex and cn_ex:
            examples.append({
                'English': process_text_cleanup(en_ex.text.strip()),
                'Chinese': process_text_cleanup(cn_ex.text.strip())
            })
    return examples

def extract_nl_definitions(nl_tab):
    """
    从“权威英汉双解”标签中提取释义，包括语法标签、动词搭配和习语。
    修复了对复杂释义结构（如 "put" 和 "king"）的解析逻辑。
    """
    definitions = []
    # 查找所有主要词性分段 (e.g., v., n.)
    segments = nl_tab.find_all('div', class_='defeachseg')
    for seg in segments:
        pos_element = seg.find('span', class_='defpos')
        pos_text = pos_element.text.strip() if pos_element else ''

        senses = []
        deflistseg = seg.find('div', class_='deflistseg')
        if deflistseg:
            # 遍历每个释义条目
            for item in deflistseg.find_all('div', class_='deflistitem'):
                sense_num_element = item.find('div', class_='defnum')
                sense_num_text = sense_num_element.text.strip() if sense_num_element else ''

                # 定位到包含真正释义的容器
                defitemcon = item.find('div', class_='defitemcon')
                if not defitemcon:
                    continue

                # 提取高级别的分组标题 (例如 "处所；位置")
                sense_group = {}
                defitemtitle = item.find('div', class_='defitemtitle')
                if defitemtitle:
                    group_cn = defitemtitle.find('span', class_='itemname')
                    group_en = defitemtitle.find('span', 'itmeval')
                    sense_group['Chinese'] = process_text_cleanup(group_cn.text.strip()) if group_cn else ''
                    sense_group['English'] = process_text_cleanup(group_en.text.strip()) if group_en else ''

                # 从 'defitemcon' 中提取具体的释义
                def_cn_element = defitemcon.find('span', class_='itemname')
                def_cn_text = process_text_cleanup(def_cn_element.text.strip()) if def_cn_element else ''

                # 英文释义通常是最后一个 'itmeval' span
                all_itmeval = defitemcon.find_all('span', class_='itmeval')
                def_en_text = process_text_cleanup(all_itmeval[-1].text.strip()) if all_itmeval else ''

                # 用法模式通常在 'strong' 标签中
                pattern = ''
                strong_tag = defitemcon.find('strong')
                if strong_tag:
                    pattern = process_text_cleanup(strong_tag.text.strip())
                
                # 提取语法标签 [i], [t]
                grammar_tags = []
                for gra in item.find_all('span', class_='defgra'):
                    tag_text = gra.text.strip()
                    if tag_text in ['[i]', '[t]']:
                        grammar_tags.append(tag_text)

                # 使用辅助函数提取例句
                examples = extract_examples(item)

                senses.append({
                    'sense_number': sense_num_text,
                    'sense_group': sense_group, # 存储高级别分组
                    'definition': {'Chinese': def_cn_text, 'English': def_en_text},
                    'pattern': pattern,
                    'grammar_tags': grammar_tags,
                    'examples': examples
                })

        # 提取习语
        idioms = []
        idom_bars = seg.find_all('div', class_='idombar')
        for idom_bar in idom_bars:
            title_bars = idom_bar.find_all('div', class_='defitemtitlebar')
            def_bars = idom_bar.find_all('div', class_='defitembar')
            
            for i, title_bar in enumerate(title_bars):
                idiom_title = title_bar.find('div', class_='defitemtitle')
                idiom_title_text = ''
                if idiom_title:
                    title_span = idiom_title.find('span', class_='itmeval')
                    if title_span:
                        idiom_title_text = process_text_cleanup(title_span.text.strip())
                
                idiom_def_cn_text = ''
                idiom_def_en_text = ''
                idiom_examples = []
                
                if i < len(def_bars):
                    def_bar = def_bars[i]
                    def_item = def_bar.find('div', class_='defitem')
                    if def_item:
                        def_item_con = def_item.find('div', class_='defitemcon')
                        if def_item_con:
                            idiom_def_cn = def_item_con.find('span', class_='itemname')
                            idiom_def_en = def_item_con.find('span', class_='itmeval')
                            idiom_def_cn_text = process_text_cleanup(idiom_def_cn.text.strip()) if idiom_def_cn else ''
                            idiom_def_en_text = process_text_cleanup(idiom_def_en.text.strip()) if idiom_def_en else ''
                        
                        idiom_examples = extract_examples(def_item)

                idioms.append({
                    'idiom': idiom_title_text,
                    'definition': {'Chinese': idiom_def_cn_text, 'English': idiom_def_en_text},
                    'examples': idiom_examples
                })

        definitions.append({
            'part_of_speech': pos_text,
            'senses': senses,
            'idioms': idioms
        })
    return definitions

def fetch_bing_dictionary(word, mkt='zh-CN', set_lang='zh', client_ver='BDDTV3.5.1.4320', form='BDVEHC'):
    """
    从必应词典抓取单词的词典条目。
    抓取“权威英汉双解”部分，并包含搭配、同义词和反义词。
    """
    # 构造带查询参数的URL
    base_url = 'https://cn.bing.com/dict/clientsearch'
    params = {
        'mkt': mkt,
        'setLang': set_lang,
        'form': form,
        'ClientVer': client_ver,
        'q': word
    }
    url = f"{base_url}?{urlencode(params)}"
    
    # 发送HTTP请求
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status() # 对 4xx/5xx 响应抛出 HTTPError
    except requests.RequestException as e:
        # 捕获网络请求异常，并重新抛出自定义异常
        raise Exception(f"Failed to fetch data for '{word}': {str(e)}")
    
    # 解析HTML内容
    soup = BeautifulSoup(response.text, 'html.parser')
    content = soup.find('div', class_='client_search_content')
    if not content:
        # 如果没有找到主要内容区域，说明查询失败或页面结构变化
        raise Exception(f"No dictionary content found for '{word}'. Possible word not found or page structure changed.")
    
    left_side = content.find('div', class_='client_search_leftside_area')
    right_side = content.find('div', class_='client_search_rightside_area')
    
    # 提取词头
    headword = left_side.find('div', class_='client_def_hd_hd').text.strip() if left_side and left_side.find('div', class_='client_def_hd_hd') else ''
    
    # 提取发音
    pronunciations = {}
    pron_lists = left_side.find_all('div', class_='client_def_hd_pn_list') if left_side else []
    if len(pron_lists) >= 2:
        pron_us_container = pron_lists[0]
        pron_uk_container = pron_lists[1]
        
        pron_us = pron_us_container.find('div', class_='client_def_hd_pn')
        if pron_us and '美' in pron_us.get_text():
            pronunciations['US'] = pron_us.get_text().replace('美', '').strip()

        pron_uk = pron_uk_container.find('div', class_='client_def_hd_pn')
        if pron_uk and '英' in pron_uk.get_text():
            pronunciations['UK'] = pron_uk.get_text().replace('英', '').strip()

    # 提取“权威英汉双解”释义
    definitions = []
    nl_tab = content.find('div', id='clientnlid') # 查找权威英汉双解的ID
    if nl_tab:
        definitions = extract_nl_definitions(nl_tab)
    else:
        # 如果没有找到权威英汉双解部分，也视为错误
        raise Exception(f"No '权威英汉双解' definitions found for '{word}'.")
            
    # 提取搭配、同义词、反义词
    collocations = []
    synonyms = []
    antonyms = []
    if right_side:
        for side_bar in right_side.find_all('div', class_='client_side_bar'):
            title = side_bar.find('div', class_='client_side_title').text.strip() if side_bar.find('div', class_='client_side_title') else ''
            if title == '搭配':
                for content_div in side_bar.find_all('div', class_='client_siderbar_content'):
                    type_ = content_div.find('span', class_='client_siderbar_list_title').text.strip() if content_div.find('span', class_='client_siderbar_list_title') else ''
                    items = [item.text.strip() for item in content_div.find_all('a', class_='client_siderbar_list_word')]
                    collocations.append({'type': type_, 'items': items})
            elif title == '同义词':
                for content_div in side_bar.find_all('div', class_='client_siderbar_content'):
                    pos = content_div.find('span', class_='client_siderbar_list_title').text.strip() if content_div.find('span', class_='client_siderbar_list_title') else ''
                    items = [item.text.strip() for item in content_div.find_all('a', class_='client_siderbar_list_word')]
                    synonyms.append({'part_of_speech': pos, 'items': items})
            elif title == '反义词':
                for content_div in side_bar.find_all('div', class_='client_siderbar_content'):
                    pos = content_div.find('span', class_='client_siderbar_list_title').text.strip() if content_div.find('span', class_='client_siderbar_list_title') else ''
                    items = [item.text.strip() for item in content_div.find_all('a', class_='client_siderbar_list_word')]
                    antonyms.append({'part_of_speech': pos, 'items': items})
    
    # 组织结果
    result = {
        'headword': headword,
        'pronunciations': pronunciations,
        'definitions': definitions, # 包含权威英汉双解
        'collocations': collocations,
        'synonyms': synonyms,
        'antonyms': antonyms
    }
    return result

# 示例用法
if __name__ == "__main__":
    # 使用 'put' 作为测试单词来验证修复效果
    word_to_test = "king" 
    try:
        result = fetch_bing_dictionary(word_to_test)
        # 使用 json.dumps เพื่อ格式化输出，便于查看
        print(json.dumps(result, ensure_ascii=False, indent=2))
    except Exception as e:
        print(f"查询 '{word_to_test}' 时发生错误: {e}")