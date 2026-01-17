# coverseer

`coverseer` is a process monitor that uses Ollama to analyze the output of a child process and automatically restart it if it detects errors, hangs, or crashes.

## Features

- **LLM-Powered Monitoring**: Uses Ollama (default: `gemma3:4b-it-qat`) to understand process health beyond simple exit codes.
- **Auto-Restart**: Kills and restarts the process if the LLM identifies a failure state or if the process exits with a non-zero code.
- **Detailed Logging**: Captures and logs all output from the child process.
- **Standalone Executable**: Supports building a single-file `.exe` for Windows.

## Requirements

- Python 3.12+
- [Ollama](https://ollama.com/) running locally.
- Python packages: `requests`, `ollama-call`.

## Usage

### Running with Python

```bash
python coverseer.py "your command here"
```

Example:
```bash
python coverseer.py "ollama pull gemma3:4b-it-qat"
```

### Configuration

You can edit `coverseer.py` to change:
- `CHECK_INTERVAL_SECONDS`: How often to poll Ollama for health checks (default: 5s).
- `MAX_OUTPUT_LINES`: How many lines of history to send to Ollama (default: 100).
- `OLLAMA_MODEL`: Which model to use (default: `gemma3:4b-it-qat`).

## Building the Executable

To create a standalone `coverseer.exe`:

1. Install PyInstaller:
   ```bash
   pip install pyinstaller
   ```
2. Run the build script:
   ```bash
   .\build_exe.bat
   ```
3. The executable will be in the `dist/` directory.

## License

MIT
