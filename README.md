# wiki-to-pdf

Convert an MkDocs project into a single styled PDF document with:

- **Markdown Preview Enhanced** (GitHub) styling
- **Mermaid diagram** rendering (converted to inline SVG)
- **Page breaks** between chapters
- **Table of Contents** for the entire document
- **Cover page** with title, subtitle, author
- **Full control** over file selection and order via your own `mkdocs.yml`

## Docker Setup (Recommended)

Using Docker avoids the need to install system dependencies like Node.js, Pango, Cairo, Chromium, and Python packages locally.

### 1. Build the Docker image

```bash
docker build -t wiki-to-pdf .
```

### 2. Generate PDF

Run the container, mounting your project directory (containing `mkdocs.yml` and `docs/`) and an output folder:

```bash
docker run --rm \
  -v $(pwd):/workspace/project \
  -v $(pwd)/pdf:/workspace/output \
  -e PDF_TITLE="My Amazing Project" \
  -e PDF_AUTHOR="Jane Doe" \
  wiki-to-pdf
```

### Docker Environment Variables

You can customize the PDF using the following environment variables. If left empty, the build script defaults to whatever is configured in your `mkdocs.yml`.

| Variable | Default | Description |
|---|---|---|
| `CONFIG_FILE` | `/workspace/project/mkdocs.yml` | Path to your `mkdocs.yml` |
| `ATTACHMENTS_DIR` | *(empty)* | Optional path to an external attachments folder to copy in |
| `OUTPUT_FILENAME` | `document.pdf` | Name of the generated file |
| `PDF_TITLE` | *(from yaml)* | Large text on the cover |
| `PDF_SUBTITLE` | *(from yaml)* | Smaller text below the title |
| `PDF_AUTHOR` | *(from yaml)* | Author name at the bottom |
| `PDF_COPYRIGHT` | *(from yaml)* | Copyright text |
| `TOC_LEVEL` | *(from yaml)* | Heading depth in the Table of Contents |
| `VERSION_TABLE` | *(empty)* | Path to a YAML/JSON file with version history entries |
| `VERSION_FROM_GIT` | *(empty)* | Set to `true` to auto-generate version table from git tags/log |
| `VERSION_EXCLUDE_PATTERN` | *(empty)* | Regex to exclude commits (e.g. `^Merge`) |

---

## Azure Pipelines Integration

An example `azure-pipelines.yml` is included in the repository. It builds the Docker image, runs the generation against your repository, and publishes the resulting PDF as a build artifact.

The pipeline executes the equivalent of:

```bash
docker run --rm \
  -v $(System.DefaultWorkingDirectory):/workspace/project \
  -v $(System.DefaultWorkingDirectory)/output:/workspace/output \
  -e PDF_TITLE="Project Architecture & API" \
  wiki-to-pdf:latest
```

When the pipeline finishes, you can download the PDF from the **Artifacts** section of the Azure DevOps build run.

---

## Local Setup (Without Docker)

### Prerequisites
- Python 3.13 (with venv)
- Node.js (for mermaid-cli)
- Pango (`brew install pango` or `apt-get install libpango-1.0-0`)
- mermaid-cli (`npm install -g @mermaid-js/mermaid-cli`)

### Installation & Usage

```bash
# Set up Python virtual environment
python3.13 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Generate the PDF based on your mkdocs.yml
python src/build_pdf.py --config mkdocs.yml --output pdf/document.pdf

# Optionally copy external attachments
python src/build_pdf.py --config mkdocs.yml --attachments-dir assets/images --output pdf/document.pdf

# Include a version history table from a YAML file
python src/build_pdf.py --config mkdocs.yml --version-table versions.yml --output pdf/document.pdf

# Auto-generate version history from git tags and commit log
python src/build_pdf.py --config mkdocs.yml --version-from-git --output pdf/document.pdf

# Auto-generate but exclude merge commits
python src/build_pdf.py --version-from-git --version-exclude-pattern "^Merge" --output pdf/document.pdf
```

### Version Table

A **Version History** table appears on a dedicated page after the cover. There are two ways to populate it:

#### Option 1: Manual YAML file (`--version-table`)

Provide a YAML file via `--version-table` (CLI) or the `VERSION_TABLE` environment variable (Docker).

```yaml
versions:
  - version: "1.0.0"
    date: "2026-04-30"
    author: "Jane Doe"
    changes: "Initial release."       # string
  - version: "0.9.0"
    date: "2026-04-01"
    author: "Jane Doe"
    changes:                            # or a list of bullet points
      - Added Docker support
      - CI/CD integration
```

#### Option 2: Auto-generate from git (`--version-from-git`)

Use git tags as version markers. Commits between consecutive tags are grouped under each version.

```bash
# Tag your releases
git tag -a v1.0.0 -m "Stable release with Mermaid support"
git tag -a v0.9.0 <sha> -m "Docker and CI/CD"
git push --tags

# Build with auto-generated version table
python src/build_pdf.py --version-from-git --output pdf/document.pdf
```

| Scenario | Result |
|---|---|
| Tags exist with commits between them | Full version table grouped by tag |
| Commits after latest tag | Shown under an "Unreleased" row |
| No tags at all | Single "Unreleased" row with recent commits |
| Not a git repo / `git` not installed | Warning printed, version table skipped |
| `--version-table` also provided | Explicit file wins, `--version-from-git` ignored |

The standalone generator script can also be used directly:

```bash
# Write to file
python src/generate_version_table.py --output versions.yml

# Print to stdout, exclude merge commits, cap at 10 per version
python src/generate_version_table.py --max-commits 10 --exclude-pattern "^Merge"
```

## How It Works

1. **Configuration:** The script parses your `mkdocs.yml` to locate your `docs_dir` and the order of your navigation (`nav:`).
2. **Copying:** It copies your docs and any specified `--attachments-dir` to a temporary workspace.
3. **Mermaid Rendering:** Mermaid code blocks (`\`\`\`mermaid` or `:::mermaid`) are rendered to SVG via `mmdc` (Puppeteer/Chromium) and embedded inline in the Markdown.
4. **MkDocs Build:** MkDocs builds the site with the `to-pdf` plugin.
5. **PDF Generation:** WeasyPrint renders the HTML into a final PDF using custom SCSS styling matching Markdown Preview Enhanced.
