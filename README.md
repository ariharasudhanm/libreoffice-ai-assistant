# LibreOffice AI Assistant

An AI-powered writing assistant extension for LibreOffice Writer. Uses a local [Ollama](https://ollama.com) server to rewrite, summarize, translate, fix grammar, and more — all without sending your data to the cloud.

## Demo

<video src="AI_Assistant_demo.mp4" width="100%" controls>
  Your browser does not support the video tag. <a href="AI_Assistant_demo.mp4">Download the demo video</a>.
</video>

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
2. **Ollama** — install from [ollama.com](https://ollama.com)
3. **A language model** — pull one with:
   ```bash
   ollama pull llama3.2
   ```
4. **Ollama running** — start the server:
   ```bash
   ollama serve
   ```

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

By default, the extension connects to Ollama at `http://localhost:11434` using the `llama3.2` model with a 120-second timeout.

To change these defaults, edit `extension/pythonpath/ollama_client.py`:

```python
DEFAULT_URL   = "http://localhost:11434"
DEFAULT_MODEL = "llama3.2"
DEFAULT_TIMEOUT = 120
```

## Troubleshooting

| Problem | Solution |
|---|---|
| "Cannot reach Ollama" | Make sure Ollama is running: `ollama serve` |
| "Timed out" | Try shorter text, or increase `DEFAULT_TIMEOUT` |
| Menu doesn't appear | Restart LibreOffice completely (all windows) |
| Extension won't install | Close ALL LibreOffice windows first, then try again |
| Nothing happens on Generate | Check that you have text selected in the document |

## Project Structure

```
extension/
├── ai_assistant.py              # Main extension: UNO component + dialog UI
├── pythonpath/
│   ├── ollama_client.py         # Ollama API client
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
