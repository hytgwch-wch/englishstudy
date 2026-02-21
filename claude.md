# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

EnglishStudy is a **personalized English vocabulary learning desktop application** built with Python and PyQt6. It implements spaced repetition (SM-2 algorithm) and ELO-based difficulty adaptation for optimized vocabulary learning.

## Development Commands

### Running the Application
```bash
python main.py
```

### Testing
```bash
# Run all tests
pytest

# Run specific test file
pytest tests/test_srs.py

# Run with coverage
pytest --cov=src --cov-report=html
```

### Code Quality
```bash
# Format code
black src/ tests/

# Lint
pylint src/

# Type check
mypy src/
```

### Installing Dependencies
```bash
pip install -r requirements.txt
```

## Architecture

This project follows a **strict layered architecture** with dependency flow from top to bottom:

```
┌─────────────────────────────────────────┐
│   Presentation Layer (src/ui/)          │  PyQt6 Widgets
├─────────────────────────────────────────┤
│   Application Layer (src/services/)     │  Business Logic Coordinators
├─────────────────────────────────────────┤
│   Domain Layer (src/core/)              │  SRS & ELO Algorithms
├─────────────────────────────────────────┤
│   Infrastructure Layer (src/infrastructure/) │  Database, File I/O, Logging
└─────────────────────────────────────────┘
```

**Key architectural rules:**
- **Never import upward**: UI cannot be imported by services; services cannot be imported by core
- **Data flows downward**: User actions → UI → Services → Core → Infrastructure
- **Models are shared**: `src/models/` contains dataclasses used across all layers

### Core Modules

| Layer | Module | Responsibility |
|-------|--------|----------------|
| `ui/` | `main_window.py` | Main entry point, view switching, session orchestration |
| `ui/widgets/` | `card_widget.py` | Flashcard display with answer buttons |
| `ui/widgets/` | `test_widget.py` | Quiz/test mode interface |
| `services/` | `study_manager.py` | Study session lifecycle, word queue management |
| `services/` | `vocab_manager.py` | Vocabulary file loading and database import |
| `core/` | `srs.py` | SM-2 spaced repetition algorithm |
| `core/` | `difficulty.py` | ELO-based difficulty adaptation |
| `infrastructure/` | `database.py` | SQLite operations with connection management |
| `infrastructure/` | `vocab_loader.py` | JSON vocabulary file parsing |

## Core Algorithms

### SM-2 Spaced Repetition (`src/core/srs.py`)

The algorithm calculates review intervals based on user feedback:

- **I(1) = 1 day**, **I(2) = 6 days**, **I(n) = I(n-1) × EF**
- **Easiness Factor (EF)**: Updated per user response, clamped to [1.3, 3.0]
- **Quality mapping**: EASY=5, MEDIUM=3, HARD=1

When modifying SRS behavior, update `QUALITY_MAP` and interval calculation methods.

### ELO Difficulty Adaptation (`src/core/difficulty.py`)

Estimates user ability and recommends appropriate word difficulty:

- **Expected score**: `P(E) = 1 / (1 + 10^((Rw - Ru) / 400))`
- **User rating update**: `Ru' = Ru + K × (Actual - Expected)`
- **Difficulty to ELO mapping**: 1→600, 5→1000, 10→2400

## Data Model

Key entities in `src/models/`:

| Model | Purpose | Key Fields |
|-------|---------|------------|
| `Vocabulary` | Word definition | word, phonetic, definition, difficulty (1-10) |
| `WordRecord` | User's progress | status, easiness, interval, next_review, state |
| `User` | Learner profile | level (elementary/cet4/etc), rating (ELO) |
| `StudySession` | Learning session | start_time, words_studied, correct_rate |

**MemoryStatus enum**: UNKNOWN → EASY/MEDIUM/HARD (user feedback)
**WordState enum**: NEW → LEARNING → REVIEW → MASTERED

## Database Schema

SQLite database at `data/user/study.db`:

- `vocabularies`: Word definitions (read-only after import)
- `word_records`: Per-user learning progress (frequently updated)
- `users`: User profiles with ELO ratings
- `mistake_book` / `new_word_book`: Special collections

**Important**: Use `DatabaseManager.get_connection()` context manager for all DB operations.

## Vocabulary File Format

JSON format in `data/vocab/`:

```json
{
  "meta": {
    "name": "词库名称",
    "level": "middle",
    "version": "1.0"
  },
  "words": [
    {
      "word": "abandon",
      "phonetic": "/əˈbændən/",
      "definition": "v. 遗弃；放弃",
      "example": "He decided to abandon the project.",
      "difficulty": 4,
      "frequency": 3
    }
  ]
}
```

## Configuration

All settings in `config.py` via the `AppConfig` dataclass:

- **SRS settings**: `SRS_MIN_EASINESS`, `SRS_MAX_EASINESS`
- **ELO settings**: `ELO_INITIAL_RATING`, `ELO_K_FACTOR`
- **UI dimensions**: `WINDOW_WIDTH`, `WINDOW_HEIGHT`
- **Paths**: All relative to project root, uses `Path` objects

## The 5-File Matrix Protocol

This project uses a strict document-driven development protocol. Before making changes:

1. **VISION.md** - Project scope and MVP definition
2. **ARCH.md** - Architecture decisions with mathematical formulas
3. **ROADMAP.md** - Task tracking with `[TODO]`/`[DOING]`/`[DONE]` statuses
4. **IMP_LOG.md** - Implementation decisions and technical debt
5. **TEST.md** - Test cases and results

**Required workflow**:
- Update `ROADMAP.md` task status to `[DOING]` before starting work
- Update `ARCH.md` before changing core algorithms or data models
- Document decisions in `IMP_LOG.md` as you make them

## Common Patterns

### Database Access
```python
from src.infrastructure.database import get_db
db = get_db()
with db.get_connection() as conn:
    cursor = conn.execute("SELECT * FROM vocabularies WHERE word = ?", (word,))
    result = cursor.fetchone()
```

### Service Manager Usage
```python
from src.services.study_manager import get_study_manager
study_mgr = get_study_manager()
queue = study_mgr.get_study_queue(user, max_new=20, max_review=50)
```

### Logging
```python
from src.infrastructure.logger import get_logger
logger = get_logger(__name__)
logger.info("User started study session")
```

## UI Styling

Dark theme using QSS (Qt Stylesheet) in `src/ui/styles/dark_theme.py`:
- Uses Catppuccin-inspired color palette
- Button class property: `setProperty("class", "primary")`
- Modify stylesheet for visual changes, not individual widget styles

## Known Limitations (Technical Debt)

Per `IMP_LOG.md`:
- User selection is hardcoded (always user ID 1)
- Vocabulary files are sample data only (~15-20 words each)
- No desktop notifications yet (planned for P1)
- Statistics visualization is text-only (charts planned for P1)

## File Paths

- **Database**: `data/user/study.db` (auto-created on first run)
- **Vocabularies**: `data/vocab/*.json`
- **Logs**: `data/user/englishstudy.log`
- All paths use `pathlib.Path` and are relative to project root

## Testing Strategy

- Unit tests for algorithms: `tests/test_srs.py`, `tests/test_difficulty.py`
- Database tests use in-memory SQLite for isolation
- UI tests use `pytest-qt` for widget interaction testing
