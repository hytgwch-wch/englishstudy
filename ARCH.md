# ARCH.md: 系统架构设计

> **版本**: 1.0
> **创建日期**: 2026-02-20
> **状态**: P2-Architecture 阶段
> **负责人**: Architect

---

## 1. 系统架构概览

### 1.1 分层架构

```
┌─────────────────────────────────────────────────────────────────┐
│                        Presentation Layer                        │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │
│  │  CardWidget  │  │  TestWidget  │  │ StatsWidget  │          │
│  │  (单词卡片)   │  │  (测试模式)   │  │  (统计面板)   │          │
│  └──────────────┘  └──────────────┘  └──────────────┘          │
├─────────────────────────────────────────────────────────────────┤
│                      Application Layer                          │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │
│  │StudyManager  │  │ TestManager  │  │VocabManager  │          │
│  │ (学习控制器)  │  │ (测试控制器)  │  │ (词库管理器)  │          │
│  └──────────────┘  └──────────────┘  └──────────────┘          │
├─────────────────────────────────────────────────────────────────┤
│                       Domain Layer                              │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │
│  │   SRS Engine │  │  Difficulty  │  │  Progress    │          │
│  │  (间隔重复)   │  │   Adapter    │  │  Tracker     │          │
│  └──────────────┘  └──────────────┘  └──────────────┘          │
├─────────────────────────────────────────────────────────────────┤
│                    Infrastructure Layer                         │
│  ┌──────────────┐  ┌──────────────┐  �──────────────┐          │
│  │  DB Manager  │  │  File I/O    │  │   Logger     │          │
│  │ (SQLite)     │  │  (JSON/CSV)  │  │  (日志系统)   │          │
│  └──────────────┘  └──────────────┘  └──────────────┘          │
└─────────────────────────────────────────────────────────────────┘
```

### 1.2 模块依赖关系

```
┌────────────────────────────────────────────────────────────────┐
│                         主程序入口                               │
│                           main.py                               │
└────────────────────────────┬───────────────────────────────────┘
                             │
                ┌────────────┴────────────┐
                │   EnglishStudyApp       │
                │   (PyQt6 QMainWindow)   │
                └────────────┬────────────┘
                             │
        ┌────────────────────┼────────────────────┐
        │                    │                    │
┌───────┴───────┐   ┌────────┴────────┐   ┌───────┴───────┐
│  StudyView    │   │   TestView      │   │  ManageView   │
│  (学习界面)    │   │   (测试界面)     │   │  (管理界面)    │
└───────────────┘   └─────────────────┘   └───────────────┘
        │                    │                    │
        └────────────────────┼────────────────────┘
                             │
                ┌────────────┴────────────┐
                │      CoreServices       │
                │  (StudyManager, etc.)   │
                └────────────┬────────────┘
                             │
        ┌────────────────────┼────────────────────┐
        │                    │                    │
┌───────┴────────┐   ┌───────┴────────┐   ┌───────┴────────┐
│  SRSEngine     │   │  Difficulty    │   │  Database      │
│  (SRS算法)      │   │  Adapter       │   │  Manager       │
└────────────────┘   └────────────────┘   └────────────────┘
```

---

## 2. 核心数据模型

### 2.1 实体关系图（ERD）

```
┌──────────────────┐       ┌──────────────────┐       ┌──────────────────┐
│     Vocabulary   │       │  WordRecord      │       │   StudySession   │
│     (词汇表)      │       │  (单词学习记录)    │       │   (学习会话)      │
├──────────────────┤       ├──────────────────┤       ├──────────────────┤
│ id: PK          │──1:N──│ id: PK          │──N:1──│ id: PK          │
│ word: VARCHAR   │       │ vocabulary_id:FK│       │ start_time: DT   │
│ phonetic: STR   │       │ user_id: INT    │       │ end_time: DT     │
│ definition: TXT │       │ status: ENUM    │       │ words_studied:INT│
│ example: TXT    │       │ easiness: FLOAT │       │ correct_rate:FLT │
│ difficulty: INT │       │ interval: INT   │       │ user_id: INT     │
│ frequency: INT  │       │ next_review: DT │       └──────────────────┘
│ category: STR   │       │ last_review: DT │                │
└──────────────────┘       │ repetitions:INT │                │
                           │ created_at: DT  │                │
                           └──────────────────┘                │
                                      │                         │
                           ┌──────────┴──────────┐             │
                           │                     │             │
                  ┌────────┴────────┐  ┌────────┴────────┐     │
                  │   MistakeBook   │  │   NewWordBook   │     │
                  │   (错题本)        │  │   (生词本)        │     │
                  ├─────────────────┤  ├─────────────────┤     │
                  │ word_record_id:│  │ word_record_id: │     │
                  │   FK (UNIQUE)  │  │   FK (UNIQUE)   │     │
                  │ note: TEXT     │  │ note: TEXT      │     │
                  │ created_at: DT │  │ created_at: DT  │     │
                  └─────────────────┘  └─────────────────┘     │
                                                                │
                                    ┌───────────────────────────┘
                                    │
                           ┌────────┴────────┐
                           │     User        │
                           │    (用户)        │
                           ├─────────────────┤
                           │ id: PK          │
                           │ name: VARCHAR   │
                           │ level: ENUM     │
                           │ created_at: DT  │
                           └─────────────────┘
```

### 2.2 数据模型定义（Python Type Hints）

```python
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional, List

class MemoryStatus(Enum):
    """记忆状态枚举"""
    UNKNOWN = "unknown"      # 未学习
    EASY = "easy"            # 认识
    MEDIUM = "medium"        # 模糊
    HARD = "hard"            # 不认识

class UserLevel(Enum):
    """用户水平"""
    ELEMENTARY = "elementary"  # 小学
    MIDDLE = "middle"         # 初中
    HIGH = "high"             # 高中
    CET4 = "cet4"             # 四级
    CET6 = "cet6"             # 六级

@dataclass
class Vocabulary:
    """词汇实体"""
    id: int
    word: str
    phonetic: Optional[str] = None
    definition: str = ""
    example: Optional[str] = None
    difficulty: int = 1          # 1-10 难度等级
    frequency: int = 1           # 词频等级
    category: Optional[str] = None

@dataclass
class WordRecord:
    """单词学习记录"""
    id: int
    vocabulary_id: int
    user_id: int
    status: MemoryStatus = MemoryStatus.UNKNOWN
    easiness: float = 2.5        # SM-2 易度因子
    interval: int = 0            # 复习间隔（天）
    repetitions: int = 0         # 复习次数
    next_review: Optional[datetime] = None
    last_review: Optional[datetime] = None
    created_at: datetime = field(default_factory=datetime.now)

@dataclass
class StudySession:
    """学习会话记录"""
    id: int
    user_id: int
    start_time: datetime
    end_time: Optional[datetime] = None
    words_studied: int = 0
    correct_rate: float = 0.0

@dataclass
class MistakeEntry:
    """错题本条目"""
    word_record_id: int
    note: str = ""
    created_at: datetime = field(default_factory=datetime.now)

@dataclass
class NewWordEntry:
    """生词本条目"""
    word_record_id: int
    note: str = ""
    created_at: datetime = field(default_factory=datetime.now)

@dataclass
class User:
    """用户实体"""
    id: int
    name: str
    level: UserLevel = UserLevel.ELEMENTARY
    created_at: datetime = field(default_factory=datetime.now)
```

---

## 3. 核心算法设计

### 3.1 SM-2 间隔重复算法

#### 3.1.1 数学定义

**基础变量定义：**

| 符号 | 含义 | 初始值 |
|------|------|--------|
| $I_n$ | 第 $n$ 次复习的间隔（天） | $I_1 = 1$ |
| $EF_n$ | 第 $n$ 次复习后的易度因子 | $EF_0 = 2.5$ |
| $R_n$ | 第 $n$ 次复习的用户评分 (0-5) | - |
| $q_n$ | 第 $n$ 次复习的质量等级 (0-5) | - |

**核心公式：**

$$
I_1 = 1 \quad \text{(首次复习间隔 1 天)}
$$

$$
I_2 = 6 \quad \text{(第二次复习间隔 6 天)}
$$

$$
I_n = I_{n-1} \times EF_{n-1}, \quad n \geq 3
$$

**易度因子更新公式：**

$$
EF'_n = EF_{n-1} + (0.1 - (5 - q_n) \times (0.08 + (5 - q_n) \times 0.02))
$$

其中用户评分 $q_n$ 与质量等级的映射：

$$
q_n = \begin{cases}
5 & \text{完全记忆（EASY）} \\
4 & \text{正确但有犹豫（MEDIUM）} \\
3 & \text{困难但正确} \\
2 & \text{错误但模糊} \\
1 & \text{完全错误（HARD）} \\
0 & \text{完全失败}
\end{cases}
$$

**边界约束：**

$$
EF_n = \max(1.3, \min(EF'_n, 3.0))
$$

#### 3.1.2 算法实现

```python
from datetime import datetime, timedelta
from typing import Tuple

class SRSEngine:
    """间隔重复系统引擎（SuperMemo-2 算法）"""

    # 用户评分到质量等级的映射
    QUALITY_MAP = {
        MemoryStatus.EASY: 5,      # 完全记忆
        MemoryStatus.MEDIUM: 3,    # 模糊/有犹豫
        MemoryStatus.HARD: 1,      # 不认识/错误
    }

    def __init__(self, min_easiness: float = 1.3, max_easiness: float = 3.0):
        self.min_easiness = min_easiness
        self.max_easiness = max_easiness

    def calculate_next_review(
        self,
        record: WordRecord,
        quality: MemoryStatus
    ) -> Tuple[int, float, datetime]:
        """
        计算下次复习时间

        Args:
            record: 当前单词学习记录
            quality: 用户评分（记忆状态）

        Returns:
            (interval, new_easiness, next_review_date)
        """
        q = self.QUALITY_MAP[quality]

        # 计算新的易度因子
        new_easiness = self._update_easiness(record.easiness, q)

        # 计算复习间隔
        new_interval = self._calculate_interval(
            record.interval,
            record.repetitions,
            new_easiness,
            q
        )

        # 计算下次复习日期
        next_review = datetime.now() + timedelta(days=new_interval)

        return new_interval, new_easiness, next_review

    def _update_easiness(self, current_ef: float, quality: int) -> float:
        """更新易度因子"""
        ef_prime = current_ef + (0.1 - (5 - quality) * (0.08 + (5 - quality) * 0.02))
        return max(self.min_easiness, min(ef_prime, self.max_easiness))

    def _calculate_interval(
        self,
        current_interval: int,
        repetitions: int,
        easiness: float,
        quality: int
    ) -> int:
        """计算复习间隔"""
        if quality < 3:
            # 答错，重置为第一天
            return 1

        if repetitions == 0:
            return 1
        elif repetitions == 1:
            return 6
        else:
            return int(current_interval * easiness)

    def get_due_words(self, records: List[WordRecord]) -> List[WordRecord]:
        """获取今日应复习的单词"""
        now = datetime.now()
        return [
            r for r in records
            if r.next_review is not None and r.next_review <= now
        ]

    def get_new_words(
        self,
        all_records: List[WordRecord],
        limit: int = 20
    ) -> List[Vocabulary]:
        """获取新单词（未学习过的）"""
        new_words = [r for r in all_records if r.status == MemoryStatus.UNKNOWN]
        return new_words[:limit]
```

### 3.2 难度自适应算法（ELO-based）

#### 3.2.1 数学定义

**变量定义：**

| 符号 | 含义 |
|------|------|
| $R_u$ | 用户能力值（初始值 1000） |
| $R_w$ | 单词难度值 |
| $K$ | 学习速率参数（默认 32） |
| $P(E)$ | 预期正确率 |

**预期正确率计算（Logistic 函数）：**

$$
P(E) = \frac{1}{1 + 10^{(R_w - R_u) / 400}}
$$

**用户能力更新公式：**

$$
R'_u = R_u + K \times (Actual - P(E))
$$

其中 $Actual \in \{0, 1\}$ 为实际结果。

**单词难度校准（可选，用于众包学习）：**

$$
R'_w = R_w - K \times (Actual - P(E))
$$

#### 3.2.2 算法实现

```python
from typing import List, Tuple
import math

class DifficultyAdapter:
    """难度自适应引擎（基于 ELO 机制）"""

    # 基础难度值映射
    DIFFICULTY_TO_ELO = {
        1: 600,   # 非常简单
        2: 800,
        3: 1000,  # 中等（基准）
        4: 1200,
        5: 1400,
        6: 1600,
        7: 1800,
        8: 2000,
        9: 2200,
        10: 2400  # 非常困难
    }

    ELO_TO_DIFFICULTY = {v: k for k, v in DIFFICULTY_TO_ELO.items()}

    def __init__(self, initial_rating: float = 1000.0, k_factor: float = 32.0):
        self.initial_rating = initial_rating
        self.k_factor = k_factor

    def expected_score(self, user_rating: float, word_difficulty: int) -> float:
        """
        计算预期正确率

        Args:
            user_rating: 用户当前能力值
            word_difficulty: 单词难度等级 (1-10)

        Returns:
            预期正确率 [0, 1]
        """
        word_rating = self.DIFFICULTY_TO_ELO.get(word_difficulty, 1000)
        return 1.0 / (1.0 + 10 ** ((word_rating - user_rating) / 400))

    def update_user_rating(
        self,
        current_rating: float,
        word_difficulty: int,
        actual_result: bool
    ) -> float:
        """
        更新用户能力值

        Args:
            current_rating: 当前能力值
            word_difficulty: 单词难度
            actual_result: 实际结果 (True=正确, False=错误)

        Returns:
            更新后的能力值
        """
        expected = self.expected_score(current_rating, word_difficulty)
        actual = 1.0 if actual_result else 0.0
        return current_rating + self.k_factor * (actual - expected)

    def recommend_difficulty(
        self,
        user_rating: float,
        target_success_rate: float = 0.7
    ) -> int:
        """
        根据用户能力推荐合适的单词难度

        Args:
            user_rating: 用户能力值
            target_success_rate: 目标正确率（默认 0.7，保持适度挑战）

        Returns:
            推荐的难度等级 (1-10)
        """
        # 反向计算：给定预期正确率，求对应的单词难度值
        # P = 1 / (1 + 10^((Rw - Ru)/400))
        # 1/P - 1 = 10^((Rw - Ru)/400)
        # log10(1/P - 1) = (Rw - Ru)/400
        # Rw = Ru + 400 * log10(1/P - 1)

        target_elo = user_rating + 400 * math.log10(1/target_success_rate - 1)

        # 找到最接近的难度等级
        closest_difficulty = 5  # 默认中等
        min_diff = float('inf')

        for difficulty, elo in self.DIFFICULTY_TO_ELO.items():
            diff = abs(elo - target_elo)
            if diff < min_diff:
                min_diff = diff
                closest_difficulty = difficulty

        return closest_difficulty

    def batch_update(
        self,
        user_rating: float,
        results: List[Tuple[int, bool]]
    ) -> float:
        """
        批量更新用户能力值

        Args:
            user_rating: 当前能力值
            results: [(difficulty, actual_result), ...] 结果列表

        Returns:
            更新后的能力值
        """
        new_rating = user_rating
        for difficulty, result in results:
            new_rating = self.update_user_rating(new_rating, difficulty, result)
        return new_rating
```

---

## 4. 接口定义

### 4.1 数据访问层接口

```python
from abc import ABC, abstractmethod
from typing import List, Optional

class IDatabaseManager(ABC):
    """数据库管理器接口"""

    @abstractmethod
    def init_database(self) -> None:
        """初始化数据库表结构"""
        pass

    @abstractmethod
    def get_word_record(self, record_id: int) -> Optional[WordRecord]:
        """获取单词学习记录"""
        pass

    @abstractmethod
    def save_word_record(self, record: WordRecord) -> bool:
        """保存/更新单词学习记录"""
        pass

    @abstractmethod
    def get_due_words(self, user_id: int) -> List[WordRecord]:
        """获取今日应复习的单词"""
        pass

    @abstractmethod
    def add_to_mistake_book(self, word_record_id: int, note: str = "") -> bool:
        """添加到错题本"""
        pass

    @abstractmethod
    def add_to_new_word_book(self, word_record_id: int, note: str = "") -> bool:
        """添加到生词本"""
        pass

    @abstractmethod
    def get_mistake_book(self, user_id: int) -> List[MistakeEntry]:
        """获取错题本"""
        pass

    @abstractmethod
    def get_new_word_book(self, user_id: int) -> List[NewWordEntry]:
        """获取生词本"""
        pass

class IVocabLoader(ABC):
    """词库加载器接口"""

    @abstractmethod
    def load_vocabulary(self, file_path: str) -> List[Vocabulary]:
        """加载词库文件"""
        pass

    @abstractmethod
    def validate_format(self, file_path: str) -> bool:
        """验证词库文件格式"""
        pass

    @abstractmethod
    def get_available_vocabularies(self) -> List[str]:
        """获取可用词库列表"""
        pass
```

### 4.2 业务逻辑层接口

```python
class IStudyManager(ABC):
    """学习管理器接口"""

    @abstractmethod
    def start_session(self, user_id: int) -> StudySession:
        """开始学习会话"""
        pass

    @abstractmethod
    def get_next_word(self, session_id: int) -> Optional[Vocabulary]:
        """获取下一个待学习单词"""
        pass

    @abstractmethod
    def submit_answer(
        self,
        session_id: int,
        word_id: int,
        status: MemoryStatus
    ) -> WordRecord:
        """提交学习结果"""
        pass

    @abstractmethod
    def end_session(self, session_id: int) -> StudySession:
        """结束学习会话"""
        pass

class ITestManager(ABC):
    """测试管理器接口"""

    @abstractmethod
    def generate_test(
        self,
        user_id: int,
        word_count: int,
        test_type: str
    ) -> List[TestQuestion]:
        """生成测试题"""
        pass

    @abstractmethod
    def submit_answer(self, question_id: int, answer: str) -> bool:
        """提交测试答案"""
        pass

    @abstractmethod
    def get_test_result(self, test_id: int) -> TestResult:
        """获取测试结果"""
        pass
```

---

## 5. 数据流向设计

### 5.1 学习流程数据流

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   用户操作   │────▶│   UI 层     │────▶│ StudyManager│
│  (点击卡片)  │     │  (CardWidget)│    │  (控制器)     │
└─────────────┘     └─────────────┘     └──────┬──────┘
                                               │
                    ┌──────────────────────────┼───────────────────┐
                    │                          │                   │
            ┌───────┴────────┐       ┌────────┴────────┐   ┌───────┴────────┐
            │   SRSEngine    │       │ Difficulty      │   │  Database       │
            │   (计算复习)    │       │   Adapter       │   │  Manager        │
            └───────────────┘       └─────────────────┘   └────────────────┘
                    │                          │                   │
                    └──────────────────────────┼───────────────────┘
                                               │
                                    ┌──────────┴──────────┐
                                    │   更新 WordRecord   │
                                    │   写入 SQLite      │
                                    └─────────────────────┘
```

### 5.2 状态机设计

```python
from enum import Enum
from typing import Optional, Dict, Callable

class WordState(Enum):
    """单词状态机"""
    NEW = "new"                    # 新词，未学习
    LEARNING = "learning"          # 学习中
    REVIEW = "review"              # 复习中
    MASTERED = "mastered"          # 已掌握

class WordStateMachine:
    """单词状态机"""

    # 状态转移规则
    TRANSITIONS: Dict[WordState, Dict[MemoryStatus, WordState]] = {
        WordState.NEW: {
            MemoryStatus.EASY: WordState.LEARNING,
            MemoryStatus.MEDIUM: WordState.LEARNING,
            MemoryStatus.HARD: WordState.LEARNING,
        },
        WordState.LEARNING: {
            MemoryStatus.EASY: WordState.REVIEW,
            MemoryStatus.MEDIUM: WordState.LEARNING,
            MemoryStatus.HARD: WordState.LEARNING,
        },
        WordState.REVIEW: {
            MemoryStatus.EASY: WordState.MASTERED,
            MemoryStatus.MEDIUM: WordState.REVIEW,
            MemoryStatus.HARD: WordState.LEARNING,
        },
        WordState.MASTERED: {
            MemoryStatus.EASY: WordState.MASTERED,
            MemoryStatus.MEDIUM: WordState.REVIEW,
            MemoryStatus.HARD: WordState.LEARNING,
        },
    }

    @classmethod
    def next_state(
        cls,
        current: WordState,
        feedback: MemoryStatus
    ) -> WordState:
        """计算下一个状态"""
        return cls.TRANSITIONS[current][feedback]
```

---

## 6. 存储方案设计

### 6.1 SQLite 表结构

```sql
-- 用户表
CREATE TABLE users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name VARCHAR(100) NOT NULL,
    level VARCHAR(20) NOT NULL DEFAULT 'elementary',
    rating FLOAT DEFAULT 1000.0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 词库表
CREATE TABLE vocabularies (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    word VARCHAR(100) NOT NULL UNIQUE,
    phonetic VARCHAR(100),
    definition TEXT NOT NULL,
    example TEXT,
    difficulty INTEGER DEFAULT 1,
    frequency INTEGER DEFAULT 1,
    category VARCHAR(50)
);

-- 单词学习记录表
CREATE TABLE word_records (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    vocabulary_id INTEGER NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'unknown',
    easiness FLOAT DEFAULT 2.5,
    interval INTEGER DEFAULT 0,
    repetitions INTEGER DEFAULT 0,
    next_review TIMESTAMP,
    last_review TIMESTAMP,
    state VARCHAR(20) DEFAULT 'new',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id),
    FOREIGN KEY (vocabulary_id) REFERENCES vocabularies(id),
    UNIQUE(user_id, vocabulary_id)
);

-- 错题本
CREATE TABLE mistake_book (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    word_record_id INTEGER NOT NULL UNIQUE,
    note TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id),
    FOREIGN KEY (word_record_id) REFERENCES word_records(id)
);

-- 生词本
CREATE TABLE new_word_book (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    word_record_id INTEGER NOT NULL UNIQUE,
    note TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id),
    FOREIGN KEY (word_record_id) REFERENCES word_records(id)
);

-- 学习会话
CREATE TABLE study_sessions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    start_time TIMESTAMP NOT NULL,
    end_time TIMESTAMP,
    words_studied INTEGER DEFAULT 0,
    correct_rate FLOAT DEFAULT 0.0,
    FOREIGN KEY (user_id) REFERENCES users(id)
);

-- 索引优化
CREATE INDEX idx_word_records_next_review ON word_records(next_review);
CREATE INDEX idx_word_records_user_vocab ON word_records(user_id, vocabulary_id);
CREATE INDEX idx_mistake_book_user ON mistake_book(user_id);
CREATE INDEX idx_new_word_book_user ON new_word_book(user_id);
```

### 6.2 词库文件格式（JSON）

```json
{
  "meta": {
    "name": "初中英语核心词汇",
    "level": "middle",
    "version": "1.0",
    "total_words": 500,
    "description": "适用于初中阶段的英语核心词汇"
  },
  "words": [
    {
      "word": "abandon",
      "phonetic": "/əˈbændən/",
      "definition": "v. 遗弃；放弃",
      "example": "He decided to abandon the project.",
      "difficulty": 4,
      "frequency": 3,
      "category": "verb"
    },
    {
      "word": "ability",
      "phonetic": "/əˈbɪləti/",
      "definition": "n. 能力；才能",
      "example": "She has the ability to solve problems.",
      "difficulty": 2,
      "frequency": 5,
      "category": "noun"
    }
  ]
}
```

---

## 7. 目录结构设计

```
englishstudy/
├── main.py                     # 应用程序入口
├── config.py                   # 配置文件
├── requirements.txt            # Python 依赖
├── README.md                   # 项目说明
├── claude.md                   # V2.0 协议
├── VISION.md                   # 项目愿景
├── ARCH.md                     # 架构设计 ✓
├── ROADMAP.md                  # 任务规划
├── IMP_LOG.md                  # 实现日志
├── TEST.md                     # 测试报告
│
├── src/
│   ├── __init__.py
│   │
│   ├── ui/                     # 表示层
│   │   ├── __init__.py
│   │   ├── main_window.py      # 主窗口
│   │   ├── widgets/
│   │   │   ├── __init__.py
│   │   │   ├── card_widget.py  # 单词卡片组件
│   │   │   ├── test_widget.py  # 测试组件
│   │   │   └── stats_widget.py # 统计组件
│   │   └── styles/
│   │       └── dark_theme.qss  # 样式表
│   │
│   ├── core/                   # 领域层
│   │   ├── __init__.py
│   │   ├── srs.py              # SRS 算法引擎
│   │   ├── difficulty.py       # 难度自适应引擎
│   │   └── state_machine.py    # 状态机
│   │
│   ├── services/               # 应用层
│   │   ├── __init__.py
│   │   ├── study_manager.py    # 学习管理器
│   │   ├── test_manager.py     # 测试管理器
│   │   └── vocab_manager.py    # 词库管理器
│   │
│   ├── models/                 # 数据模型
│   │   ├── __init__.py
│   │   ├── user.py
│   │   ├── vocabulary.py
│   │   ├── word_record.py
│   │   └── session.py
│   │
│   └── infrastructure/         # 基础设施层
│       ├── __init__.py
│       ├── database.py         # 数据库管理
│       ├── vocab_loader.py     # 词库加载器
│       └── logger.py           # 日志系统
│
├── data/
│   ├── vocab/                  # 内置词库
│   │   ├── elementary.json
│   │   ├── middle_school.json
│   │   ├── high_school.json
│   │   ├── cet4.json
│   │   └── cet6.json
│   └── user/                   # 用户数据目录
│       └── .gitkeep
│
└── tests/
    ├── __init__.py
    ├── test_srs.py
    ├── test_difficulty.py
    └── test_database.py
```

---

## 8. 技术栈确认

| 组件 | 技术选型 | 版本 |
|------|----------|------|
| **GUI 框架** | PyQt6 | 6.6+ |
| **数据库** | SQLite3 | (Python 内置) |
| **数据验证** | Pydantic | 2.0+ |
| **日志** | Python logging | (内置) |
| **测试** | pytest | 7.0+ |

---

## 9. 架构设计总结

| 设计决策 | 理由 |
|----------|------|
| **分层架构** | 职责分离，便于测试和维护 |
| **依赖注入** | 接口驱动，降低模块耦合 |
| **状态机模式** | 明确单词学习流程，易于扩展 |
| **SQLite 本地存储** | 零配置，事务支持，适合单机应用 |
| **SM-2 + ELO 双算法** | 成熟算法组合，覆盖复习调度与难度适配 |

---

**ARCH.md 已完成。**

**是否进入下一阶段（P3: Planning）进行任务拆解？**
