# LibreOffice AI Assistant

An AI-powered writing assistant extension for LibreOffice Writer. Uses a local AI server ([Ollama](https://ollama.com) or [LM Studio](https://lmstudio.ai)) to rewrite, summarize, translate, fix grammar, and more — all without sending your data to the cloud.

## Demo

<!-- Replace the URL below with the one GitHub generates when you drag-drop the video into an Issue -->
[https://github.com/user-attachments/assets/REPLACE_WITH_YOUR_VIDEO_URL](https://github.com/user-attachments/assets/7968880b-92bb-4933-8c74-829bfa1d5b9d)

## Features

| Action | Description |
|---|---|
| **Rewrite** | Rewrite selected text with adjustable tone (Formal, Concise, Academic) |
| **Summarize** | Condense text to 30–40% of original length |
| **Grammar Fix** | Fix grammar, spelling, and punctuation errors |
| **Translate** | Translate text to any language |
| **Continue Writing** | Continue text in the same style and tone |
| **Simplify** | Rewrite complex text in plain, clear language |
| **Custom Prompt** | Send any instruction to the AI with selected text |

All actions include an **editable Result Preview** — review and clean up the AI output before applying it to your document.

## Prerequisites

1. **LibreOffice** (tested on Linux, should work on macOS/Windows)
2. **An AI backend** — choose one (or both):

   **Option A: Ollama** (recommended)
   ```bash
   # Install from https://ollama.com, then:
   ollama pull llama3.2
   ollama serve
   ```

   **Option B: LM Studio**
   - Download from [lmstudio.ai](https://lmstudio.ai)
   - Load a model in the app
   - Start the local server (runs on `localhost:1234`)

## Installation

### From Release (.oxt file)

1. Download `lo-ai-assistant.oxt` from [Releases](../../releases)
2. **Close all LibreOffice windows** completely
3. Open LibreOffice Writer
4. Go to **Tools → Extension Manager**
5. Click **Add** and select the `.oxt` file
6. Click **Close** and **restart LibreOffice**

### From Source

```bash
git clone https://github.com/ariharasudhanm/libreoffice-ai-assistant.git
cd libreoffice-ai-assistant
./build_extension.sh
```

Then install the generated `lo-ai-assistant.oxt` as described above.

## Usage

1. Open a document in **LibreOffice Writer**
2. **Select some text** you want to process
3. Go to **AI Assistant → Open AI Assistant...** in the menu bar
4. Choose an **Action** (Rewrite, Summarize, Grammar Fix, etc.)
5. Optionally set **Tone** (for Rewrite) or type **Additional Instructions**
6. Click **Generate** — the AI processes your text
7. Review the **Result Preview** (you can edit it before applying)
8. Click **Apply** to replace the selected text (or insert as comment)

### Tips

- **Continue Writing** appends after your text instead of replacing it
- **Translate** — type the target language in the instructions field (e.g., "Spanish")
- **Custom Prompt** — type any instruction (e.g., "Convert to bullet points")
- The dialog stays open so you can process multiple selections without reopening it
- Click **Refresh** to update the selection preview after selecting new text

## Configuration

The dialog includes an **AI Backend** selector at the top to switch between Ollama and LM Studio.

| Backend | Default URL | Default Model |
|---|---|---|
| **Ollama** | `http://localhost:11434` | `llama3.2` |
| **LM Studio** | `http://localhost:1234` | (auto-detected) |

To change these defaults, edit `extension/pythonpath/ollama_client.py`:

```python
BACKENDS = {
    "ollama": {
        "url": "http://localhost:11434/api/generate",
        "model": "llama3.2",
    },
    "lmstudio": {
        "url": "http://127.0.0.1:1234/v1/chat/completions",
        "model": "default",
    },
}
```

## Troubleshooting

| Problem | Solution |
|---|---|
| "Cannot reach AI server" | Make sure Ollama (`ollama serve`) or LM Studio server is running |
| "Timed out" | Try shorter text, or increase `DEFAULT_TIMEOUT_S` in `ollama_client.py` |
| Menu doesn't appear | Restart LibreOffice completely (all windows) |
| Extension won't install | Close ALL LibreOffice windows first, then try again |
| Nothing happens on Generate | Check that you have text selected in the document |
| Wrong backend selected | Check the **AI Backend** selector at the top of the dialog |

## Project Structure

```
extension/
├── ai_assistant.py              # Main extension: UNO component + dialog UI
├── pythonpath/
│   ├── ollama_client.py         # AI backend client (Ollama + LM Studio)
│   └── prompts.py               # Prompt templates for all actions
├── registry/
│   └── Addons.xcu               # Menu configuration
├── assets/
│   └── icon.png                 # Extension icon
├── description/
│   └── desc.en.txt              # Extension description text
├── META-INF/
│   └── manifest.xml             # Extension manifest
└── description.xml              # Extension metadata
```

## License

[MIT](LICENSE)
