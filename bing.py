import requests
from bs4 import BeautifulSoup
import json
from urllib.parse import urlencode

def fetch_bing_dictionary(word, mkt='zh-CN', set_lang='zh', client_ver='BDDTV3.5.1.4320', form='BDVEHC'):
    """
    Fetch and parse dictionary entry from Bing Dictionary for a given word.
    
    Args:
        word (str): The word to look up.
        mkt (str): Market code (default: 'zh-CN').
        set_lang (str): Language setting (default: 'zh').
        client_ver (str): Client version (default: 'BDDTV3.5.1.4320').
        form (str): Form parameter (default: 'BDVEHC').
    
    Returns:
        dict: Structured dictionary containing headword, pronunciations, definitions,
              collocations, synonyms, and antonyms.
    """
    # Construct URL with query parameters
    base_url = 'https://cn.bing.com/dict/clientsearch'
    params = {
        'mkt': mkt,
        'setLang': set_lang,
        'form': form,
        'ClientVer': client_ver,
        'q': word
    }
    url = f"{base_url}?{urlencode(params)}"
    
    # Send HTTP request
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    try:
        response = requests.get(url, headers=headers, timeout=5)
        response.raise_for_status()
    except requests.RequestException as e:
        return {'error': f"Failed to fetch data: {str(e)}"}
    
    # Parse HTML content
    soup = BeautifulSoup(response.text, 'html.parser')
    content = soup.find('div', class_='client_search_content')
    if not content:
        return {'error': 'No dictionary content found'}
    
    left_side = content.find('div', class_='client_search_leftside_area')
    right_side = content.find('div', class_='client_search_rightside_area')
    
    # Extract headword
    headword = left_side.find('div', class_='client_def_hd_hd').text.strip() if left_side and left_side.find('div', class_='client_def_hd_hd') else ''
    
    # Extract pronunciations
    pronunciations = {}
    pron_lists = left_side.find_all('div', class_='client_def_hd_pn_list') if left_side else []
    if len(pron_lists) >= 2:
        pron_us = pron_lists[0].find('div', class_='client_def_hd_pn')
        pron_uk = pron_lists[1].find('div', class_='client_def_hd_pn')
        if pron_us and ':' in pron_us.text:
            pronunciations['US'] = pron_us.text.split(':')[1].strip()
        if pron_uk and ':' in pron_uk.text:
            pronunciations['UK'] = pron_uk.text.split(':')[1].strip()
    
    # Extract definitions from tabs
    definitions = {}
    
    # "权威英汉双解" tab
    nl_tab = content.find('div', id='clientnlid')
    if nl_tab:
        definitions['权威英汉双解'] = extract_nl_definitions(nl_tab)
    
    # "英汉" tab
    cross_tab = content.find('div', id='clientcrossid')
    if cross_tab:
        definitions['英汉'] = extract_simple_definitions(cross_tab)
    
    # "英英" tab
    homo_tab = content.find('div', id='clienthomoid')
    if homo_tab:
        definitions['英英'] = extract_simple_definitions(homo_tab)
    
    # Extract collocations, synonyms, antonyms
    collocations = []
    synonyms = []
    antonyms = []
    if right_side:
        for side_bar in right_side.find_all('div', class_='client_side_bar'):
            title = side_bar.find('div', class_='client_side_title').text.strip() if side_bar.find('div', class_='client_side_title') else ''
            if title == '搭配':
                for content in side_bar.find_all('div', class_='client_siderbar_content'):
                    type_ = content.find('span', class_='client_siderbar_list_title').text.strip() if content.find('span', class_='client_siderbar_list_title') else ''
                    items = [item.text.strip() for item in content.find_all('a', class_='client_siderbar_list_word')]
                    collocations.append({'type': type_, 'items': items})
            elif title == '同义词':
                for content in side_bar.find_all('div', class_='client_siderbar_content'):
                    pos = content.find('span', class_='client_siderbar_list_title').text.strip() if content.find('span', class_='client_siderbar_list_title') else ''
                    items = [item.text.strip() for item in content.find_all('a', class_='client_siderbar_list_word')]
                    synonyms.append({'part_of_speech': pos, 'items': items})
            elif title == '反义词':
                for content in side_bar.find_all('div', class_='client_siderbar_content'):
                    pos = content.find('span', class_='client_siderbar_list_title').text.strip() if content.find('span', class_='client_siderbar_list_title') else ''
                    items = [item.text.strip() for item in content.find_all('a', class_='client_siderbar_list_word')]
                    antonyms.append({'part_of_speech': pos, 'items': items})
    
    # Organize the result
    result = {
        'headword': headword,
        'pronunciations': pronunciations,
        'definitions': definitions,
        'collocations': collocations,
        'synonyms': synonyms,
        'antonyms': antonyms
    }
    return result

def extract_nl_definitions(nl_tab):
    """Extract definitions from '权威英汉双解' tab, including idioms."""
    definitions = []
    segments = nl_tab.find_all('div', class_='defeachseg')
    for seg in segments:
        pos = seg.find('span', class_='defpos')
        pos_text = pos.text.strip() if pos else ''
        
        senses = []
        deflistseg = seg.find('div', class_='deflistseg')
        if deflistseg:
            for item in deflistseg.find_all('div', class_='deflistitem'):
                sense_num = item.find('div', class_='defnum')
                sense_num_text = sense_num.text.strip() if sense_num else ''
                sense_label = item.find('div', class_='defitemtitle')
                sense_label_text = sense_label.text.strip() if sense_label else ''
                def_cn = item.find('span', class_='itemname')
                def_cn_text = def_cn.text.strip() if def_cn else ''
                def_en = item.find('span', class_='itmeval')
                def_en_text = def_en.text.strip() if def_en else ''
                
                examples = []
                for ex in item.find_all('div', class_='examlistitem'):
                    en_ex = ex.find('div', class_='examitmeval')
                    cn_ex = ex.find('div', class_='examitemname')
                    if en_ex and cn_ex:
                        examples.append({
                            'English': en_ex.text.strip(),
                            'Chinese': cn_ex.text.strip()
                        })
                
                senses.append({
                    'sense_number': sense_num_text,
                    'sense_label': sense_label_text,
                    'definition': {'Chinese': def_cn_text, 'English': def_en_text},
                    'examples': examples
                })
        
        idioms = []
        for idom in seg.find_all('div', class_='idombar'):
            idiom_title = idom.find('div', class_='defitemtitle')
            idiom_title_text = idiom_title.text.strip() if idiom_title else ''
            idiom_def_cn = idom.find('span', class_='itemname')
            idiom_def_cn_text = idiom_def_cn.text.strip() if idiom_def_cn else ''
            idiom_def_en = idom.find('span', class_='itmeval')
            idiom_def_en_text = idiom_def_en.text.strip() if idiom_def_en else ''
            
            idiom_examples = []
            for ex in idom.find_all('div', class_='examlistitem'):
                en_ex = ex.find('div', class_='examitmeval')
                cn_ex = ex.find('div', class_='examitemname')
                if en_ex and cn_ex:
                    idiom_examples.append({
                        'English': en_ex.text.strip(),
                        'Chinese': cn_ex.text.strip()
                    })
            
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

def extract_simple_definitions(tab):
    """Extract simple definitions from '英汉' or '英英' tabs."""
    definitions = []
    for bar in tab.find_all('div', class_='client_def_bar'):
        pos = bar.find('span', class_='client_def_title')
        pos_text = pos.text.strip() if pos else ''
        defs = []
        for item in bar.find_all('div', class_='client_def_list_item'):
            def_content = item.find('div', class_='client_def_list_word_content')
            if def_content:
                defs.append(def_content.text.strip())
        if defs:
            definitions.append({
                'part_of_speech': pos_text,
                'definitions': defs
            })
    return definitions

# Example usage
if __name__ == "__main__":
    word = "clear"
    result = fetch_bing_dictionary(word)
    print(json.dumps(result, ensure_ascii=False, indent=2))