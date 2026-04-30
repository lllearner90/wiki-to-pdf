#!/usr/bin/env python3
"""
wiki-to-pdf build script with Mermaid diagram rendering.

This script:
1. Reads your mkdocs.yml (where you define 'nav' and order).
2. Copies the docs directory and any attachments to a temp build folder.
3. Pre-processes Markdown files to render Mermaid diagrams as SVG.
4. Updates mkdocs.yml with cover page overrides from CLI/ENV.
5. Runs mkdocs build with the to-pdf plugin.
6. Outputs a styled PDF matching Markdown Preview Enhanced (GitHub) look.

Usage:
    python build_pdf.py [--config mkdocs.yml] [--attachments-dir path/to/assets]
"""

import argparse
import glob
import os
import platform
import re
import shutil
import subprocess
import sys
import tempfile
import yaml


# ---------------------------------------------------------------------------
# Native library path fix for WeasyPrint (Pango / GLib / Cairo)
# ---------------------------------------------------------------------------

def _ensure_native_lib_paths():
    """Ensure the dynamic linker can find gobject / pango / cairo.

    - macOS (local):  Add Homebrew lib dirs to DYLD_FALLBACK_LIBRARY_PATH.
    - Linux (CI/Docker): Add common lib dirs to LD_LIBRARY_PATH when the
      standard paths are not already searched (e.g. slim containers).
    """
    system = platform.system()

    if system == 'Darwin':
        env_var = 'DYLD_FALLBACK_LIBRARY_PATH'
        candidates = ['/opt/homebrew/lib', '/usr/local/lib']
    elif system == 'Linux':
        env_var = 'LD_LIBRARY_PATH'
        candidates = [
            '/usr/lib/x86_64-linux-gnu',   # Debian / Ubuntu amd64
            '/usr/lib/aarch64-linux-gnu',  # Debian / Ubuntu arm64
            '/usr/lib64',                  # RHEL / Fedora
            '/usr/local/lib',
        ]
    else:
        return

    current = os.environ.get(env_var, '')
    additions = [p for p in candidates
                 if os.path.isdir(p) and p not in current]
    if additions:
        new_value = ':'.join(additions + ([current] if current else []))
        os.environ[env_var] = new_value

_ensure_native_lib_paths()


# ---------------------------------------------------------------------------
# Mermaid helpers
# ---------------------------------------------------------------------------

def find_mermaid_blocks(content: str) -> list[tuple[int, int, str]]:
    """Find all mermaid code blocks and return their positions and content."""
    blocks = []
    pattern = re.compile(r'(```|:::)mermaid\s*\n(.*?)\n\1', re.DOTALL)
    for match in pattern.finditer(content):
        blocks.append((match.start(), match.end(), match.group(2).strip()))
    return blocks


def render_mermaid_to_svg(mermaid_code: str, output_path: str) -> bool:
    """Render a mermaid diagram to SVG using mmdc CLI."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.mmd', delete=False) as f:
        f.write(mermaid_code)
        input_path = f.name

    # Puppeteer config for headless Chromium (needed in Docker)
    puppet_cfg = os.environ.get('PUPPETEER_CONFIG')
    cmd = ['mmdc', '-i', input_path, '-o', output_path,
           '-b', 'transparent', '--scale', '2']
    if puppet_cfg and os.path.isfile(puppet_cfg):
        cmd += ['-p', puppet_cfg]

    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=60
        )
        if result.returncode != 0:
            print(f"mmdc error: {result.stderr.strip()}", file=sys.stderr)
            return False
        return True
    except FileNotFoundError:
        print("mmdc not found. Install: npm i -g @mermaid-js/mermaid-cli",
              file=sys.stderr)
        return False
    except subprocess.TimeoutExpired:
        print("mmdc timed out", file=sys.stderr)
        return False
    finally:
        os.unlink(input_path)


def clean_svg_for_inline(svg_path: str) -> str:
    """Read SVG file and clean it for inline embedding."""
    with open(svg_path, 'r') as f:
        svg_content = f.read()
    svg_content = re.sub(r'<\?xml[^?]*\?>\s*', '', svg_content)
    svg_content = svg_content.replace('<svg ', '<svg class="mermaid-svg" ', 1)
    return svg_content


def preprocess_markdown(src_path: str, img_dir: str) -> int:
    """Process a markdown file in place, converting mermaid blocks to inline SVG."""
    with open(src_path, 'r') as f:
        content = f.read()

    blocks = find_mermaid_blocks(content)
    if not blocks:
        return 0

    filename_base = os.path.splitext(os.path.basename(src_path))[0]
    new_content = content
    offset = 0
    rendered = 0

    for i, (start, end, mermaid_code) in enumerate(blocks):
        svg_filename = f"{filename_base}_mermaid_{i}.svg"
        svg_path = os.path.join(img_dir, svg_filename)

        print(f"Rendering Mermaid diagram {i+1}/{len(blocks)} in {os.path.basename(src_path)}...")

        if render_mermaid_to_svg(mermaid_code, svg_path):
            svg_inline = clean_svg_for_inline(svg_path)
            replacement = (
                f'\n<div class="mermaid-diagram" '
                f'style="text-align: center; margin: 20px 0;">\n'
                f'{svg_inline}\n</div>\n'
            )
            rendered += 1
        else:
            replacement = (
                f'```\nMermaid diagram could not be rendered\n\n'
                f'{mermaid_code}\n```'
            )

        new_content = (
            new_content[:start + offset]
            + replacement
            + new_content[end + offset:]
        )
        offset += len(replacement) - (end - start)

    with open(src_path, 'w') as f:
        f.write(new_content)

    return rendered


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description='Convert Markdown files to PDF with Mermaid support based on mkdocs.yml')
    parser.add_argument('--config', '-c', default='mkdocs.yml',
                        help='Path to mkdocs.yml (default: mkdocs.yml)')
    parser.add_argument('--attachments-dir', '-a', action='append',
                        help='Additional directories to copy into the docs folder (can specify multiple)')
    parser.add_argument('--output', '-o', default='pdf/document.pdf',
                        help='Output PDF path (default: pdf/document.pdf)')
    
    # PDF Cover Overrides
    parser.add_argument('--title', default=None, help='Override cover page title')
    parser.add_argument('--subtitle', default=None, help='Override cover page subtitle')
    parser.add_argument('--author', default=None, help='Override author shown on cover page')
    parser.add_argument('--copyright', default=None, help='Override copyright line on cover page')
    parser.add_argument('--toc-level', type=int, default=None, help='Override table of contents heading depth')
    
    parser.add_argument('--version-table', default=None,
                        help='Path to a YAML/JSON file with version history entries for the PDF cover')
    parser.add_argument('--keep-temp', action='store_true',
                        help='Keep temporary working directory')
    args = parser.parse_args()

    project_dir = os.path.dirname(os.path.abspath(__file__))
    config_path = os.path.abspath(args.config)

    if not os.path.isfile(config_path):
        print(f"Config file not found: {config_path}", file=sys.stderr)
        sys.exit(1)

    # 1. Read mkdocs.yml
    with open(config_path, 'r') as f:
        try:
            config = yaml.safe_load(f)
        except yaml.YAMLError as exc:
            print(f"Error parsing {config_path}: {exc}", file=sys.stderr)
            sys.exit(1)

    # Find docs_dir
    original_docs_dir = config.get('docs_dir', 'docs')
    original_docs_dir_path = os.path.join(os.path.dirname(config_path), original_docs_dir)

    if not os.path.isdir(original_docs_dir_path):
        print(f"docs_dir not found: {original_docs_dir_path}", file=sys.stderr)
        sys.exit(1)

    # 2. Create working directory
    work_dir = tempfile.mkdtemp(prefix='mkdocs-pdf-')
    temp_docs_dir = os.path.join(work_dir, 'docs')
    temp_config_path = os.path.join(work_dir, 'mkdocs.yml')
    img_dir = os.path.join(temp_docs_dir, 'img')
    
    print(f"\nWorking directory: {work_dir}")

    # Copy docs_dir to temp_docs_dir
    print(f"Copying docs from {original_docs_dir_path}...")
    shutil.copytree(original_docs_dir_path, temp_docs_dir)
    os.makedirs(img_dir, exist_ok=True)

    # Copy additional attachments if specified
    if args.attachments_dir:
        for attachment in args.attachments_dir:
            att_path = os.path.abspath(attachment)
            if os.path.isdir(att_path):
                dest_name = os.path.basename(att_path)
                dest_path = os.path.join(temp_docs_dir, dest_name)
                print(f"Copying attachments from {att_path} to {dest_path}...")
                if os.path.exists(dest_path):
                    # Merge directories if it already exists
                    shutil.copytree(att_path, dest_path, dirs_exist_ok=True)
                else:
                    shutil.copytree(att_path, dest_path)
            else:
                print(f"Warning: Attachment directory not found: {att_path}", file=sys.stderr)

    # 3. Pre-process Mermaid diagrams
    print("\nPre-processing Mermaid diagrams...")
    md_files = glob.glob(os.path.join(temp_docs_dir, '**', '*.md'), recursive=True)
    total_diagrams = 0
    for md_file in md_files:
        count = preprocess_markdown(md_file, img_dir)
        total_diagrams += count
    print(f"Rendered {total_diagrams} Mermaid diagram(s)")

    # 4. Update mkdocs.yml with overrides
    print("\nUpdating mkdocs.yml configuration...")
    config['docs_dir'] = 'docs'
    config['site_dir'] = 'site'
    
    # Ensure plugins list exists
    if 'plugins' not in config:
        config['plugins'] = []
    
    # Find to-pdf plugin config or add it
    to_pdf_plugin = None
    for i, plugin in enumerate(config['plugins']):
        if isinstance(plugin, dict) and 'to-pdf' in plugin:
            to_pdf_plugin = plugin['to-pdf']
            break
        elif plugin == 'to-pdf':
            config['plugins'][i] = {'to-pdf': {}}
            to_pdf_plugin = config['plugins'][i]['to-pdf']
            break
            
    if to_pdf_plugin is None:
        to_pdf_plugin = {}
        config['plugins'].append({'to-pdf': to_pdf_plugin})

    # Apply overrides
    to_pdf_plugin['output_path'] = args.output
    
    # Set template path to absolute path of project templates if not specified
    if 'custom_template_path' not in to_pdf_plugin:
        to_pdf_plugin['custom_template_path'] = os.path.join(project_dir, 'templates')
    else:
        # If user specified a relative path in their mkdocs.yml, make it absolute
        # based on the original mkdocs.yml location
        user_tpl_path = to_pdf_plugin['custom_template_path']
        if not os.path.isabs(user_tpl_path):
            to_pdf_plugin['custom_template_path'] = os.path.join(os.path.dirname(config_path), user_tpl_path)

    if args.title is not None:
        to_pdf_plugin['cover_title'] = args.title
    if args.subtitle is not None:
        to_pdf_plugin['cover_subtitle'] = args.subtitle
    if args.author is not None:
        to_pdf_plugin['author'] = args.author
    if args.copyright is not None:
        to_pdf_plugin['copyright'] = args.copyright
    if args.toc_level is not None:
        to_pdf_plugin['toc_level'] = args.toc_level
        to_pdf_plugin['ordered_chapter_level'] = args.toc_level

    # 4b. Load version table data and inject into extra context
    if 'extra' not in config:
        config['extra'] = {}

    version_table_file = args.version_table or os.environ.get('VERSION_TABLE')
    if version_table_file:
        vt_path = os.path.abspath(version_table_file)
        if os.path.isfile(vt_path):
            print(f"Loading version table from {vt_path}...")
            with open(vt_path, 'r') as f:
                vt_data = yaml.safe_load(f)
            # Accept either {versions: [...]} or a bare list
            if isinstance(vt_data, list):
                config['extra']['version_table'] = vt_data
            elif isinstance(vt_data, dict) and 'versions' in vt_data:
                config['extra']['version_table'] = vt_data['versions']
            else:
                print(f"Warning: version table file has unexpected format. "
                      f"Expected a list or dict with 'versions' key.",
                      file=sys.stderr)
        else:
            print(f"Warning: Version table file not found: {vt_path}",
                  file=sys.stderr)

    # Write updated config
    with open(temp_config_path, 'w') as f:
        yaml.dump(config, f, sort_keys=False)

    # 5. Find mkdocs binary (venv → global)
    print("\nBuilding PDF with mkdocs + to-pdf plugin...")
    venv_mkdocs = os.path.join(project_dir, '.venv', 'bin', 'mkdocs')
    if not os.path.exists(venv_mkdocs):
        venv_mkdocs = shutil.which('mkdocs')
    if not venv_mkdocs:
        print("mkdocs not found.", file=sys.stderr)
        sys.exit(1)

    result = subprocess.run(
        [venv_mkdocs, 'build', '-f', temp_config_path],
        cwd=work_dir,
        capture_output=True,
        text=True,
    )

    if result.returncode != 0:
        print(f"\nmkdocs build failed:\n{result.stderr}", file=sys.stderr)
        if not args.keep_temp:
            shutil.rmtree(work_dir, ignore_errors=True)
        sys.exit(1)

    # 6. Copy PDF to final location
    generated_pdf = os.path.join(work_dir, 'site', args.output)
    if os.path.exists(generated_pdf):
        final_output = os.path.join(project_dir, args.output)
        os.makedirs(os.path.dirname(final_output), exist_ok=True)
        shutil.copy2(generated_pdf, final_output)
        pdf_size = os.path.getsize(final_output)
        print(f"\nPDF generated successfully!")
        print(f"   {final_output}")
        print(f"   Size: {pdf_size / 1024:.1f} KB")
    else:
        print(
            f"\nPDF not found at: {generated_pdf}", file=sys.stderr
        )
        if not args.keep_temp:
            shutil.rmtree(work_dir, ignore_errors=True)
        sys.exit(1)

    # Cleanup
    if args.keep_temp:
        print(f"\nTemp directory kept: {work_dir}")
    else:
        shutil.rmtree(work_dir, ignore_errors=True)
        print(f"Temp files cleaned up")


if __name__ == '__main__':
    main()
