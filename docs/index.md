# Introduction

**wiki-to-pdf** is a robust toolchain designed to convert an MkDocs project into a single, beautifully styled PDF document. It solves the common challenges of PDF generation from Markdown, particularly when dealing with complex, dynamic elements like **Mermaid diagrams**.

## Key Features

- **Mermaid Diagram Support:** Automatically pre-renders Mermaid diagrams (````mermaid` or `:::mermaid`) into SVG graphics so they display perfectly in your PDF.
- **Rich Styling:** Implements GitHub-like styles (based on Markdown Preview Enhanced) tailored for printing and PDF reading.
- **Document Structure:** Generates page breaks between chapters automatically.
- **Table of Contents:** Creates an accurate, clickable table of contents for the entire document.
- **Cover Page:** Fully customizable cover page with your title, subtitle, author, and copyright information.
- **Docker Ready:** Avoid dependency nightmares by running everything securely inside a pre-configured Docker container.
- **Custom Attachments:** Supports pulling in external asset directories (like shared images) before rendering.

## Why this tool?

Most wiki-to-pdf plugins (such as `wiki-to-pdf`) rely on WeasyPrint under the hood. While WeasyPrint is excellent at converting HTML/CSS to PDF, it **does not support JavaScript execution**. 

Because standard Mermaid diagrams require a browser's JavaScript engine to render, standard MkDocs PDF tools often produce PDFs where Mermaid blocks appear as empty space or raw code.

**wiki-to-pdf** acts as a powerful pre-processor. It scans your documentation, leverages the Mermaid CLI (`mmdc`) to pre-render every diagram into a static SVG, and seamlessly embeds it before running the final WeasyPrint step. The result is a perfect, offline-ready PDF with all of your charts intact.
