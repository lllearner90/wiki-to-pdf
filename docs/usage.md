# Usage Guide

Once you have set up **wiki-to-pdf**, you can easily generate PDFs from any standard MkDocs repository. 

## Docker Usage

To generate a PDF via Docker, mount your project directory and an output directory into the container.

```bash
docker run --rm \
  -v $(pwd):/workspace/project \
  -v $(pwd)/pdf:/workspace/output \
  -e PDF_TITLE="My Amazing Project" \
  -e PDF_AUTHOR="Jane Doe" \
  wiki-to-pdf
```

### Environment Variables

You can customize the PDF using the following environment variables. If left empty, the script gracefully falls back to the values defined inside your `mkdocs.yml`.

| Variable | Default Path / Value | Description |
|---|---|---|
| `CONFIG_FILE` | `/workspace/project/mkdocs.yml` | Path to your `mkdocs.yml` |
| `ATTACHMENTS_DIR` | *(empty)* | Optional path to an external attachments folder to copy into the docs |
| `OUTPUT_FILENAME` | `document.pdf` | File name for the final PDF output |
| `PDF_TITLE` | *(from mkdocs.yml)* | Large title displayed on the cover |
| `PDF_SUBTITLE` | *(from mkdocs.yml)* | Smaller subtitle text below the title |
| `PDF_AUTHOR` | *(from mkdocs.yml)* | Author name at the bottom of the cover |
| `PDF_COPYRIGHT` | *(from mkdocs.yml)* | Copyright string |
| `TOC_LEVEL` | *(from mkdocs.yml)* | Heading depth to include in the Table of Contents |

---

## Local CLI Usage

If you installed the toolchain natively, you can run `build_pdf.py` directly from your terminal.

```bash
# Basic usage
python build_pdf.py --config mkdocs.yml --output pdf/document.pdf

# With overrides and external attachments
python build_pdf.py \
  --config mkdocs.yml \
  --attachments-dir assets/shared-images \
  --title "System Architecture" \
  --author "DevOps Team" \
  --output my-docs.pdf
```

### Available CLI Flags

Run `python build_pdf.py --help` for a full list of arguments:

- `--config`, `-c`: Path to your `mkdocs.yml`
- `--attachments-dir`, `-a`: Additional directories to copy into your docs folder (can be specified multiple times)
- `--output`, `-o`: Output PDF path
- `--title`: Override the cover page title
- `--subtitle`: Override the cover page subtitle
- `--author`: Override the author shown on the cover page
- `--copyright`: Override the copyright line
- `--toc-level`: Override the table of contents depth
- `--keep-temp`: Keep the temporary working directory for debugging purposes
