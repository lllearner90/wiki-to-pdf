# Setup Guide

You can run **wiki-to-pdf** either using Docker (recommended) or natively on your local machine.

---

## 🐳 Docker Setup (Recommended)

Using Docker is strongly recommended because PDF generation tools and diagram renderers require heavy system dependencies like Chromium, Node.js, Pango, and Cairo. Docker encapsulates all of this.

### 1. Build the Docker image

Clone the repository and build the container from the root directory:

```bash
docker build -t wiki-to-pdf .
```

### 2. Ready to use

Once the image is built, you can run the container to generate a PDF for any MkDocs project. See the [Usage](usage.md) guide for runtime commands.

---

## 💻 Local Setup (Without Docker)

If you prefer to run the script natively, ensure your machine meets the prerequisites.

### Prerequisites

- **Python 3.13** (with `venv` support)
- **Node.js** (required to run `mermaid-cli`)
- **Pango & Cairo** (required for WeasyPrint rendering)
  - *macOS:* `brew install pango`
  - *Ubuntu:* `sudo apt-get install libpango-1.0-0 libpangocairo-1.0-0`
- **mermaid-cli:** Install globally via npm:
  ```bash
  npm install -g @mermaid-js/mermaid-cli
  ```

### Installation

1. Navigate to the project root.
2. Set up a Python virtual environment:
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   ```
3. Install the required Python packages:
   ```bash
   pip install -r requirements.txt
   ```

You are now ready to generate PDFs locally by running the `build_pdf.py` script.
