"""
下载开源词库并转换格式
从 KyleBing/english-vocabulary GitHub 仓库下载词汇数据
"""
import json
import sys
import io
import urllib.request
from pathlib import Path
from typing import List, Dict, Any

# 设置 stdout 为 UTF-8 编码
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# 词汇文件映射 (GitHub 仓库中的文件名 -> 我们的目标文件名)
VOCABULARY_FILES = {
    "elementary": [
        "ChuZhong_2.json",
        "ChuZhong_3.json",
    ],
    "high_school": [
        "GaoZhong_2.json",
        "GaoZhong_3.json",
    ],
    "cet4": [
        "CET4_1.json",
        "CET4_2.json",
        "CET4_3.json",
    ],
    "cet6": [
        "CET6_1.json",
        "CET6_2.json",
        "CET6_3.json",
    ],
}

# 基础 URL
BASE_URL = "https://raw.githubusercontent.com/KyleBing/english-vocabulary/master/json_original/json-simple/"

# 难度映射
DIFFICULTY_MAP = {
    "elementary": 3,
    "high_school": 5,
    "cet4": 6,
    "cet6": 7,
}

# 分类映射 (根据词性推测)
CATEGORY_MAP = {
    "n": "noun",
    "v": "verb",
    "adj": "adjective",
    "adv": "adverb",
    "prep": "preposition",
    "conj": "conjunction",
    "pron": "pronoun",
    "interj": "interjection",
    "num": "numeral",
    "art": "article",
}


def download_json(file_name: str) -> List[Dict[str, Any]]:
    """下载单个 JSON 文件"""
    url = BASE_URL + file_name
    print(f"正在下载: {url}")

    try:
        with urllib.request.urlopen(url, timeout=30) as response:
            data = json.loads(response.read().decode('utf-8'))
            print(f"  ✓ 成功获取 {len(data)} 个单词")
            return data
    except Exception as e:
        print(f"  ✗ 下载失败: {e}")
        return []


def convert_word(source_word: Dict[str, Any], level: str) -> Dict[str, Any]:
    """将源格式转换为目标格式"""
    word = source_word.get("word", "")

    # 获取翻译和词性
    translations = source_word.get("translations", [])
    if translations:
        # 取第一个翻译作为主要释义
        translation_obj = translations[0]
        cn_translation = translation_obj.get("translation", "")
        pos_type = translation_obj.get("type", "")

        # 组合所有翻译作为完整释义
        all_translations = []
        for t in translations:
            trans = t.get("translation", "")
            pos = t.get("type", "")
            if trans:
                all_translations.append(f"{cn_translation}")
        definition = "; ".join(all_translations) if all_translations else cn_translation

        # 映射词性到我们的分类
        category = CATEGORY_MAP.get(pos_type.lower(), "noun")
    else:
        definition = ""
        category = "noun"

    # 构建例句 (从短语中选择一个)
    phrases = source_word.get("phrases", [])
    if phrases:
        phrase_obj = phrases[0]
        example = f"{phrase_obj.get('phrase', '')} - {phrase_obj.get('translation', '')}"
    else:
        example = f"Learn the word: {word}."

    # 获取难度和频率
    difficulty = DIFFICULTY_MAP.get(level, 5)
    frequency = 3  # 默认频率

    # 生成简单音标 (模拟)
    phonetic = f"/{word}/"

    return {
        "word": word,
        "phonetic": phonetic,
        "definition": f"{definition}",
        "example": example,
        "difficulty": difficulty,
        "frequency": frequency,
        "category": category
    }


def process_level(level_name: str, source_files: List[str], output_dir: Path):
    """处理单个等级的词汇"""
    print(f"\n{'='*50}")
    print(f"处理 {level_name} 词汇")
    print(f"{'='*50}")

    all_words = []
    existing_words = set()

    # 下载并合并所有文件
    for file_name in source_files:
        words = download_json(file_name)
        for word in words:
            word_text = word.get("word", "")
            if word_text and word_text not in existing_words:
                converted = convert_word(word, level_name)
                all_words.append(converted)
                existing_words.add(word_text)

    print(f"\n总计去重后: {len(all_words)} 个单词")

    # 保存到文件
    output_file = output_dir / f"{level_name}.json"

    # 检查文件是否存在
    if output_file.exists():
        print(f"文件 {output_file.name} 已存在，跳过。")
        # 还是显示统计信息
        with open(output_file, 'r', encoding='utf-8') as f:
            existing_data = json.load(f)
            print(f"现有文件包含 {len(existing_data.get('words', []))} 个单词")
        return

    # 构建输出格式
    level_display = {
        "elementary": "初中",
        "high_school": "高中",
        "cet4": "四级",
        "cet6": "六级"
    }

    output_data = {
        "meta": {
            "name": f"{level_display[level_name]}英语核心词汇",
            "level": level_display[level_name],
            "version": "1.0",
            "description": f"适用于{level_display[level_name]}阶段的核心词汇",
            "total_words": len(all_words),
            "source": "KyleBing/english-vocabulary"
        },
        "words": all_words
    }

    # 保存文件
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(output_data, f, ensure_ascii=False, indent=2)

    print(f"✓ 已保存到: {output_file}")
    print(f"  总词汇数: {len(all_words)}")


def main():
    """主函数"""
    vocab_dir = Path(__file__).parent.parent / "data" / "vocab"
    vocab_dir.mkdir(parents=True, exist_ok=True)

    print("开始下载并转换词库...")
    print(f"输出目录: {vocab_dir}")

    # 处理每个等级
    for level_name, source_files in VOCABULARY_FILES.items():
        try:
            process_level(level_name, source_files, vocab_dir)
        except Exception as e:
            print(f"处理 {level_name} 时出错: {e}")
            import traceback
            traceback.print_exc()

    print("\n" + "="*50)
    print("词库下载完成！")
    print("="*50)

    # 显示最终统计
    print("\n最终统计:")
    for level_name in VOCABULARY_FILES.keys():
        file_path = vocab_dir / f"{level_name}.json"
        if file_path.exists():
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                word_count = len(data.get("words", []))
                print(f"  {level_name}: {word_count} 个单词")


if __name__ == "__main__":
    main()
