# Contributing to AI Interview Agent

First off, thank you for considering contributing to AI Interview Agent! It's people like you that make the open-source community such an amazing place to learn, inspire, and create.

## 🚀 Getting Started

1. **Fork the Repository**: Create your own copy of the project.
2. **Setup Local Environment**:
   ```powershell
   python -m venv .venv
   .venv\Scripts\activate
   pip install -r requirements.txt
   ```
3. **Configure Environment Variables**:
   Copy `.env.example` to `.env` and add your `GEMINI_API_KEY` or `HF_API_TOKEN`.

## 🛠️ Development Workflow

### Adding New Skill Mappings
The core matching logic relies on `services/skill_mappings.py`.
- **Synonyms**: Add strict equivalences to `SKILL_SYNONYMS`.
- **Hierarchy**: Add parent-child relationships to `SKILL_HIERARCHY`.
- **Context**: Add contextual keywords to `SEMANTIC_RELATIONS`.

### Running Tests
Before submitting a PR, ensure the LLM integration is working:
```powershell
python test_llm.py
python test_models.py
```

## 📜 Coding Guidelines
- **Type Hints**: Use type hints for all function signatures.
- **Async/Await**: Use async calls for all I/O bound operations (API calls).
- **Validation**: Ensure all request/response models are defined in `models/schemas.py` using Pydantic.
- **JSON Safety**: Use `utils/json_parser.py` when handling LLM outputs.

## 📬 Submitting Changes
1. Create a new branch: `git checkout -b feature/your-feature-name`.
2. Commit your changes with descriptive messages.
3. Push to your fork and open a Pull Request.

## ⚖️ License
By contributing, you agree that your contributions will be licensed under its MIT License.
