"""
扩展词库脚本 - 为各个等级添加更多词汇
"""
import json
import sys
import io
from pathlib import Path

# 设置 stdout 为 UTF-8 编码
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# 扩展的小学词汇 (难度 1-2)
ELEMENTARY_WORDS = [
    {"word": "apple", "phonetic": "/ˈæpl/", "definition": "n. 苹果", "example": "I like to eat apples.", "difficulty": 1, "frequency": 5, "category": "noun"},
    {"word": "book", "phonetic": "/bʊk/", "definition": "n. 书", "example": "This is my book.", "difficulty": 1, "frequency": 5, "category": "noun"},
    {"word": "cat", "phonetic": "/kæt/", "definition": "n. 猫", "example": "The cat is cute.", "difficulty": 1, "frequency": 5, "category": "noun"},
    {"word": "dog", "phonetic": "/dɒɡ/", "definition": "n. 狗", "example": "I have a dog.", "difficulty": 1, "frequency": 5, "category": "noun"},
    {"word": "egg", "phonetic": "/eɡ/", "definition": "n. 蛋", "example": "I eat an egg for breakfast.", "difficulty": 1, "frequency": 5, "category": "noun"},
    {"word": "fish", "phonetic": "/fɪʃ/", "definition": "n. 鱼", "example": "Fish live in water.", "difficulty": 1, "frequency": 5, "category": "noun"},
    {"word": "girl", "phonetic": "/ɡɜːl/", "definition": "n. 女孩", "example": "She is a nice girl.", "difficulty": 1, "frequency": 5, "category": "noun"},
    {"word": "hat", "phonetic": "/hæt/", "definition": "n. 帽子", "example": "Wear your hat.", "difficulty": 1, "frequency": 5, "category": "noun"},
    {"word": "ice", "phonetic": "/aɪs/", "definition": "n. 冰", "example": "The ice is cold.", "difficulty": 1, "frequency": 5, "category": "noun"},
    {"word": "jump", "phonetic": "/dʒʌmp/", "definition": "v. 跳", "example": "Can you jump high?", "difficulty": 1, "frequency": 5, "category": "verb"},
    {"word": "key", "phonetic": "/kiː/", "definition": "n. 钥匙", "example": "Where is my key?", "difficulty": 1, "frequency": 5, "category": "noun"},
    {"word": "lion", "phonetic": "/ˈlaɪən/", "definition": "n. 狮子", "example": "The lion is strong.", "difficulty": 1, "frequency": 5, "category": "noun"},
    {"word": "moon", "phonetic": "/muːn/", "definition": "n. 月亮", "example": "The moon is bright.", "difficulty": 1, "frequency": 5, "category": "noun"},
    {"word": "nose", "phonetic": "/nəʊz/", "definition": "n. 鼻子", "example": "I have a small nose.", "difficulty": 1, "frequency": 5, "category": "noun"},
    {"word": "orange", "phonetic": "/ˈɒrɪndʒ/", "definition": "n. 橙子", "example": "Oranges are sweet.", "difficulty": 1, "frequency": 5, "category": "noun"},
    {"word": "pig", "phonetic": "/pɪɡ/", "definition": "n. 猪", "example": "The pig is pink.", "difficulty": 1, "frequency": 5, "category": "noun"},
    {"word": "queen", "phonetic": "/kwiːn/", "definition": "n. 女王", "example": "The queen is kind.", "difficulty": 1, "frequency": 5, "category": "noun"},
    {"word": "rain", "phonetic": "/reɪn/", "definition": "n. 雨", "example": "I like the rain.", "difficulty": 1, "frequency": 5, "category": "noun"},
    {"word": "star", "phonetic": "/stɑːr/", "definition": "n. 星星", "example": "Look at the stars.", "difficulty": 1, "frequency": 5, "category": "noun"},
    {"word": "tree", "phonetic": "/triː/", "definition": "n. 树", "example": "The tree is tall.", "difficulty": 1, "frequency": 5, "category": "noun"},
    {"word": "run", "phonetic": "/rʌn/", "definition": "v. 跑", "example": "I can run fast.", "difficulty": 1, "frequency": 5, "category": "verb"},
    {"word": "walk", "phonetic": "/wɔːk/", "definition": "v. 走", "example": "Let's walk home.", "difficulty": 1, "frequency": 5, "category": "verb"},
    {"word": "play", "phonetic": "/pleɪ/", "definition": "v. 玩", "example": "Let's play games.", "difficulty": 1, "frequency": 5, "category": "verb"},
    {"word": "eat", "phonetic": "/iːt/", "definition": "v. 吃", "example": "I eat lunch at noon.", "difficulty": 1, "frequency": 5, "category": "verb"},
    {"word": "drink", "phonetic": "/drɪŋk/", "definition": "v. 喝", "example": "Drink some water.", "difficulty": 1, "frequency": 5, "category": "verb"},
    {"word": "sleep", "phonetic": "/sliːp/", "definition": "v. 睡觉", "example": "I sleep at night.", "difficulty": 1, "frequency": 5, "category": "verb"},
    {"word": "happy", "phonetic": "/ˈhæpi/", "definition": "adj. 快乐的", "example": "I am happy today.", "difficulty": 1, "frequency": 5, "category": "adjective"},
    {"word": "sad", "phonetic": "/sæd/", "definition": "adj. 伤心的", "example": "Don't be sad.", "difficulty": 1, "frequency": 5, "category": "adjective"},
    {"word": "big", "phonetic": "/bɪɡ/", "definition": "adj. 大的", "example": "The elephant is big.", "difficulty": 1, "frequency": 5, "category": "adjective"},
    {"word": "small", "phonetic": "/smɔːl/", "definition": "adj. 小的", "example": "The bird is small.", "difficulty": 1, "frequency": 5, "category": "adjective"},
    {"word": "good", "phonetic": "/ɡʊd/", "definition": "adj. 好的", "example": "You are a good student.", "difficulty": 1, "frequency": 5, "category": "adjective"},
    {"word": "bad", "phonetic": "/bæd/", "definition": "adj. 坏的", "example": "That's a bad idea.", "difficulty": 1, "frequency": 5, "category": "adjective"},
]

# 扩展的高中词汇 (难度 4-6)
HIGH_SCHOOL_WORDS = [
    {"word": "abandon", "phonetic": "/əˈbændən/", "definition": "v. 遗弃；放弃", "example": "Don't abandon your dreams.", "difficulty": 5, "frequency": 3, "category": "verb"},
    {"word": "benefit", "phonetic": "/ˈbenɪfɪt/", "definition": "n. 利益；好处", "example": "Exercise has many benefits.", "difficulty": 5, "frequency": 4, "category": "noun"},
    {"word": "complex", "phonetic": "/kəmˈpleks/", "definition": "adj. 复杂的", "example": "This problem is complex.", "difficulty": 5, "frequency": 4, "category": "adjective"},
    {"word": "decade", "phonetic": "/ˈdekeɪd/", "definition": "n. 十年", "example": "A decade has passed.", "difficulty": 5, "frequency": 3, "category": "noun"},
    {"word": "economy", "phonetic": "/ɪˈkɒnəmi/", "definition": "n. 经济", "example": "The economy is growing.", "difficulty": 5, "frequency": 4, "category": "noun"},
    {"word": "factor", "phonetic": "/ˈfæktər/", "definition": "n. 因素", "example": "Many factors affect success.", "difficulty": 5, "frequency": 4, "category": "noun"},
    {"word": "generation", "phonetic": "/ˌdʒenəˈreɪʃn/", "definition": "n. 一代人；产生", "example": "Our generation faces new challenges.", "difficulty": 5, "frequency": 4, "category": "noun"},
    {"word": "harvest", "phonetic": "/ˈhɑːrvɪst/", "definition": "n. 收获", "example": "The harvest was good this year.", "difficulty": 5, "frequency": 3, "category": "noun"},
    {"word": "incident", "phonetic": "/ˈɪnsɪdənt/", "definition": "n. 事件", "example": "The incident was reported.", "difficulty": 5, "frequency": 3, "category": "noun"},
    {"word": "justice", "phonetic": "/ˈdʒʌstɪs/", "definition": "n. 正义", "example": "Justice must be served.", "difficulty": 5, "frequency": 3, "category": "noun"},
    {"word": "kernel", "phonetic": "/ˈkɜːrnl/", "definition": "n. 核心", "example": "The kernel of the argument.", "difficulty": 5, "frequency": 2, "category": "noun"},
    {"word": "launch", "phonetic": "/lɔːntʃ/", "definition": "v. 发射；发起", "example": "They launched a new project.", "difficulty": 5, "frequency": 4, "category": "verb"},
    {"word": "mechanism", "phonetic": "/ˈmekənɪzəm/", "definition": "n. 机制", "example": "This mechanism works well.", "difficulty": 5, "frequency": 3, "category": "noun"},
    {"word": "negative", "phonetic": "/ˈneɡətɪv/", "definition": "adj. 负面的；消极的", "example": "Don't be negative.", "difficulty": 5, "frequency": 4, "category": "adjective"},
    {"word": "obstacle", "phonetic": "/ˈɒbstəkl/", "definition": "n. 障碍", "example": "Overcome every obstacle.", "difficulty": 5, "frequency": 3, "category": "noun"},
    {"word": "philosophy", "phonetic": "/fəˈlɒsəfi/", "definition": "n. 哲学", "example": "Philosophy teaches thinking.", "difficulty": 6, "frequency": 3, "category": "noun"},
]

# 扩展的六级词汇 (难度 7-9)
CET6_WORDS = [
    {"word": "abstract", "phonetic": "/ˈæbstrækt/", "definition": "adj. 抽象的", "example": "Truth is an abstract concept.", "difficulty": 7, "frequency": 3, "category": "adjective"},
    {"word": "barrier", "phonetic": "/ˈbæriər/", "definition": "n. 障碍；屏障", "example": "Language can be a barrier.", "difficulty": 7, "frequency": 3, "category": "noun"},
    {"word": "collapse", "phonetic": "/kəˈlæps/", "definition": "v. 倒塌；崩溃", "example": "The bridge may collapse.", "difficulty": 7, "frequency": 3, "category": "verb"},
    {"word": "deteriorate", "phonetic": "/dɪˈtɪəriəreɪt/", "definition": "v. 恶化", "example": "His health deteriorated.", "difficulty": 7, "frequency": 2, "category": "verb"},
    {"word": "elaborate", "phonetic": "/ɪˈlæbərət/", "definition": "adj. 精心制作的", "example": "An elaborate plan.", "difficulty": 7, "frequency": 3, "category": "adjective"},
    {"word": "fabricate", "phonetic": "/ˈfæbrɪkeɪt/", "definition": "v. 捏造；制造", "example": "Don't fabricate stories.", "difficulty": 7, "frequency": 2, "category": "verb"},
    {"word": "guarantee", "phonetic": "/ˌɡærənˈtiː/", "definition": "v. 保证", "example": "I guarantee success.", "difficulty": 7, "frequency": 4, "category": "verb"},
    {"word": "hypothesis", "phonetic": "/haɪˈpɒθəsɪs/", "definition": "n. 假设", "example": "Test your hypothesis.", "difficulty": 7, "frequency": 2, "category": "noun"},
    {"word": "inherent", "phonetic": "/ɪnˈhɪərənt/", "definition": "adj. 固有的；内在的", "example": "Risks are inherent.", "difficulty": 7, "frequency": 3, "category": "adjective"},
    {"word": "jurisdiction", "phonetic": "/ˌdʒʊərɪsˈdɪkʃn/", "definition": "n. 管辖权", "example": "This is under our jurisdiction.", "difficulty": 8, "frequency": 2, "category": "noun"},
]


def load_vocab(file_path: Path) -> dict:
    """加载现有词库"""
    if file_path.exists():
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {"meta": {}, "words": []}


def save_vocab(file_path: Path, vocab: dict):
    """保存词库"""
    # 更新 meta 信息
    vocab["meta"]["total_words"] = len(vocab["words"])
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(vocab, f, ensure_ascii=False, indent=2)


def extend_vocab(file_path: Path, new_words: list, level_name: str):
    """扩展现有词库"""
    vocab = load_vocab(file_path)

    # 获取现有单词的 word 集合
    existing_words = {w["word"] for w in vocab["words"]}

    # 添加新单词
    added_count = 0
    for word in new_words:
        if word["word"] not in existing_words:
            vocab["words"].append(word)
            existing_words.add(word["word"])
            added_count += 1

    # 更新 meta
    vocab["meta"]["name"] = f"{level_name}英语核心词汇"
    vocab["meta"]["level"] = level_name.lower()
    vocab["meta"]["version"] = "1.0"
    vocab["meta"]["description"] = f"适用于{level_name}阶段的核心词汇"

    # 保存
    save_vocab(file_path, vocab)
    print(f"✓ {file_path.name}: 新增 {added_count} 个单词，总计 {len(vocab['words'])} 个")


def main():
    """主函数"""
    vocab_dir = Path(__file__).parent.parent / "data" / "vocab"

    # 扩展小学词库
    extend_vocab(
        vocab_dir / "elementary.json",
        ELEMENTARY_WORDS,
        "小学"
    )

    # 扩展高中词库 (创建新文件)
    extend_vocab(
        vocab_dir / "high_school.json",
        HIGH_SCHOOL_WORDS,
        "高中"
    )

    # 扩展六级词库 (创建新文件)
    extend_vocab(
        vocab_dir / "cet6.json",
        CET6_WORDS,
        "六级"
    )

    print("\n词库扩展完成！")


if __name__ == "__main__":
    main()
