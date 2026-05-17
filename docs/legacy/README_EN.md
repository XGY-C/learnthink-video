# Manim Video API Service (LangGraph Edition)

A LangGraph-based multi-agent video generation API service for converting structured requests into Manim code, rendering videos, repairing failures, and uploading final artifacts to Alibaba Cloud OSS.

## What changed

This edition refactors the orchestration layer to **LangGraph**:

- `StateGraph` drives the workflow
- each agent/tool is wrapped as a graph node
- routing uses conditional edges
- retries and failure handling are modeled in graph state
- learning/notice updates happen as a state transition, not an ad hoc loop

## Graph flow

```text
START
  -> initialize_task
  -> plan_request
  -> load_notices
  -> generate_code
  -> render_code
      ├─ success -> upload_video -> END
      └─ failed  -> diagnose_errors
                     -> validate_previous_fix
                     -> decide_next_step
                          ├─ retry -> repair_code -> increment_attempt -> render_code
                          └─ fail  -> finalize_failure -> END
```

## Quick start

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
uvicorn app.main:app --reload --reload-dir app --reload-exclude "runtime/*"
# Windows PowerShell alternative:
# .\start_dev.ps1
```

## LLM Integration with DeepSeek Thinking Mode

This service now supports **DeepSeek's Thinking Mode** for enhanced code generation, error diagnosis, and repair accuracy.

### Key Features

- 🧠 **Thinking Mode**: Enables chain-of-thought reasoning for complex tasks
- 🎯 **Multiple Models**: Support for deepseek-v4-pro, deepseek-v3, deepseek-coder, and more
- ⚙️ **Configurable Effort**: Choose between `high` and `max` reasoning effort
- 📊 **Enhanced Logging**: Monitor thinking process length and response times

### Quick Configuration

1. Copy the example configuration:
   ```bash
   cp .env.deepseek.example .env
   ```

2. Edit `.env` with your API credentials:
   ```bash
   ENABLE_LLM_ASSIST=true
   LLM_PROVIDER=deepseek
   LLM_BASE_URL=https://api.deepseek.com/v1
   LLM_API_KEY=your_api_key_here
   LLM_MODEL=deepseek-v4-pro
   DEEPSEEK_ENABLE_THINKING=true
   DEEPSEEK_REASONING_EFFORT=max
   ```

3. Test your configuration:
   ```bash
   python test_deepseek_thinking.py
   ```

For detailed setup instructions, see [DeepSeek Thinking Guide](../DEEPSEEK_THINKING_GUIDE.md).

## Project Structure

For a detailed overview of the project file structure, see [Project File Structure](../PROJECT_FILE_STRUCTURE.md).

For complete documentation index, see [docs/README.md](../README.md).

Quick cleanup:
```bash
# Clean runtime directory (generated videos, logs, cache)
# Windows
.\cleanup_runtime.bat

# Linux/Mac
chmod +x cleanup_runtime.sh
./cleanup_runtime.sh

# Clean entire project (cache, temp files, etc.)
# Windows
.\cleanup_project.bat

# Linux/Mac
chmod +x cleanup_project.sh
./cleanup_project.sh
```

## Notes

- Requires Python 3.11+
- Rendering still requires Manim Community + FFmpeg in the runtime environment
- Dev reload excludes `runtime/*` to avoid restart loops when generated files are written under `runtime/tasks`
- OSS upload requires valid Alibaba Cloud OSS credentials
- The service can operate without OSS upload when `OSS_ENABLED=false`
- LangGraph is used for orchestration, while deterministic tools still handle rendering, file IO, and upload
