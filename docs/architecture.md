# Architecture & Workflow

Understanding how **wiki-to-pdf** processes your files can be helpful if you need to debug failures or modify the rendering pipeline.

## The Generation Pipeline

When you trigger the build, the following sequence occurs:

1. **Configuration Parsing:** 
   The `build_pdf.py` script reads your provided `mkdocs.yml` to identify where your documentation lives (`docs_dir`) and the structure of your site (`nav`).

2. **Workspace Isolation:** 
   It creates an isolated, temporary directory and copies your documentation files along with any specified external attachments (`--attachments-dir`). This ensures your original source repository is never modified.

3. **Mermaid Pre-processing:**
   The script traverses all Markdown files in the temporary directory. 
   - It identifies standard Mermaid blocks (` ```mermaid `) and alternative blocks (`:::mermaid`).
   - For every block, it uses the Mermaid CLI (`mmdc`) to spawn a headless Chromium instance and renders the diagram into a high-quality SVG file.
   - The original text block in the Markdown is replaced with a `<div>` containing the newly rendered inline SVG.

4. **Configuration Overrides:**
   A temporary `mkdocs.yml` is generated. Any CLI arguments or environment variables (like title, author, or TOC level) are injected dynamically, updating the settings for the `to-pdf` plugin.

5. **MkDocs Build:**
   The script invokes the standard `mkdocs build` command against the temporary workspace. The `to-pdf` plugin takes over, parses the HTML, and passes it to the WeasyPrint rendering engine. Because the Mermaid diagrams are already standard SVG images, WeasyPrint includes them flawlessly.

6. **Output and Cleanup:**
   The final `.pdf` is moved to your desired output path, and the temporary workspace is completely cleaned up (unless `--keep-temp` was provided).

:::mermaid
graph TD
    A[Read mkdocs.yml] --> B[Copy to Temp Workspace]
    B --> C[Find Mermaid Blocks]
    C --> D[Run mmdc & Inject SVG]
    D --> E[Inject CLI/Env Overrides]
    E --> F[Run mkdocs build]
    F --> G[to-pdf Plugin + WeasyPrint]
    G --> H[Final PDF Generated]
:::
