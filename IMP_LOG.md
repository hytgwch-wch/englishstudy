# IMP_LOG.md: 实现日志

> **版本**: 1.0
> **创建日期**: 2026-02-20
> **状态**: P4-Build 阶段
> **负责人**: Senior Engineer

---

## 实现决策记录

| 日期 | 决策内容 | 理由 | 影响 |
|------|----------|------|------|
| 2026-02-20 | 选择 PyQt6 作为 GUI 框架 | 跨平台支持、Python 原生集成、丰富的 UI 组件 | UI 层架构 |
| 2026-02-20 | SQLite 作为本地数据库 | 零配置、事务支持、适合单机应用 | 数据存储层 |
| 2026-02-20 | SM-2 算法实现间隔重复 | 成熟算法、被 Anki/AnkiMobile 验证 | 复习调度逻辑 |
| 2026-02-20 | ELO 机制实现难度自适应 | 心理测量学标准、适合自适应学习 | 难度推荐系统 |
| 2026-02-20 | QSS 实现暗色主题 | Qt 原生支持、易于维护、Catppuccin 配色 | 视觉设计 |
| 2026-02-20 | JSON 格式存储词库 | 易于编辑、支持元数据、可版本控制 | 词库文件格式 |

---

## 技术债务追踪

| 债务项 | 描述 | 优先级 | 计划解决日期 |
|--------|------|--------|--------------|
| P1-1 | 智能复习调度 UI | 当前只有算法，缺少用户界面 | P1 阶段 |
| P1-2 | 学习进度统计图表 | 数据已收集，待可视化 | P1 阶段 |
| P1-3 | TTS 发音功能 | 需要 QtSpeech 或第三方库 | P1 阶段 |
| P1-4 | 桌面通知提醒 | 需要 PyQt6 通知系统集成 | P1 阶段 |
| P0-1 | 用户选择/创建界面 | 当前硬编码用户 ID | MVP 后期 |
| P0-2 | 词库数据完整性 | 示例词库仅 15-20 词 | RESOLVED ✓ |

---

## 遇到的问题与解决方案

| 日期 | 问题描述 | 解决方案 | 状态 |
|------|----------|----------|------|
| 2026-02-20 | PyQt6 样式表加载路径问题 | 使用 Path(__file__).parent 解析相对路径 | RESOLVED |

---

## 开发日志

### 2026-02-21 - 词库扩展与Bug修复 ✓

**词库下载完成：**

从 [KyleBing/english-vocabulary](https://github.com/KyleBing/english-vocabulary) 开源仓库下载完整词库：

| 等级 | 单词数量 | 文件 |
|------|----------|------|
| 初中 (elementary) | 1,991 | data/vocab/elementary.json |
| 高中 (high_school) | 3,753 | data/vocab/high_school.json |
| 四级 (cet4) | 4,544 | data/vocab/cet4.json |
| 六级 (cet6) | 3,992 | data/vocab/cet6.json |

**数据格式：**
- JSON 格式，包含 word, phonetic, definition, example, difficulty, frequency, category
- 来源：KyleBing/english-vocabulary (GitHub 开源项目)
- 已转换为应用标准格式

**Bug 修复：**

1. **学习卡片按钮重叠问题**
   - 修改 `src/ui/widgets/card_widget.py`
   - 添加 QScrollArea 确保内容可滚动
   - 设置水平滚动条始终关闭

2. **测试选项显示问题**
   - 修改 `src/ui/widgets/test_widget.py`
   - 添加 A/B/C/D 标签
   - 改用垂直布局固定选项位置

**脚本文件：**
- `scripts/download_vocabularies.py` - 词库下载和转换脚本

---

### 2026-02-21 - 端到端测试完成 ✓

**测试结果：**

#### 核心算法单元测试
- **SRS 算法测试** (`tests/test_srs.py`): 19/19 通过
  - 间隔计算测试
  - 易度因子更新测试
  - 复习次数跟踪测试
  - 学习队列生成测试
  - 边界条件测试

- **ELO 算法测试** (`tests/test_difficulty.py`): 25/25 通过
  - ELO 评分转换测试
  - 预期正确率计算测试
  - 用户评分更新测试
  - 难度推荐测试
  - 性能水平评估测试

**总计**: 44 个测试用例全部通过

---

### 2026-02-20 - MVP 开发完成 ✓

**已完成任务：**

#### Infrastructure 层 (I-1 ~ I-5) ✓
- [x] I-1: 项目目录结构初始化
- [x] I-2: 配置文件开发 (config.py)
- [x] I-3: 日志系统搭建 (logger.py)
- [x] I-4: SQLite 数据库初始化 (database.py)
- [x] I-5: 词库加载器开发 (vocab_loader.py)

#### Models 层 (M-1 ~ M-5) ✓
- [x] M-1: 用户模型 (user.py)
- [x] M-2: 词汇模型 (vocabulary.py)
- [x] M-3: 单词记录模型 (word_record.py)
- [x] M-4: 学习会话模型 (session.py)
- [x] M-5: 错题本/生词本模型 (notebook.py)

#### Core 层 (C-1 ~ C-3) ✓
- [x] C-1: SM-2 间隔重复算法 (srs.py)
- [x] C-2: ELO 难度自适应算法 (difficulty.py)
- [x] C-3: 单词状态机 (state_machine.py)

#### Services 层 (S-1 ~ S-3) ✓
- [x] S-1: 词库管理服务 (vocab_manager.py)
- [x] S-2: 学习管理服务 (study_manager.py)
- [x] S-3: 测试管理服务 (test_manager.py)

#### UI 层 (U-1 ~ U-5) ✓
- [x] U-1: 主窗口框架 (main_window.py)
- [x] U-2: 单词卡片组件 (card_widget.py)
- [x] U-3: 测试组件 (test_widget.py)
- [x] U-4: 词库管理界面 (vocab_manage_widget.py)
- [x] U-5: 样式表开发 (dark_theme.qss)

#### Integration 层 (INT-1 ~ INT-4) ✓
- [x] INT-1: 应用程序入口 (main.py)
- [x] INT-2: 词库数据准备 (data/vocab/*.json)
- [x] INT-3: 依赖管理 (requirements.txt)
- [x] INT-4: 文档更新 (IMP_LOG.md)

**代码统计：**
- Python 文件：~20 个
- 总代码行数：~3500+ 行
- UI 组件：4 个主要 Widget
- 词库文件：3 个示例词库（小学/初中/CET4）

**下一步：**
1. 端到端测试
2. P1 功能开发（统计图表、通知提醒、TTS）
3. 打包发布（PyInstaller）
