# =============================================================================
# Stage 1: Build image with all dependencies for wiki-to-pdf
# =============================================================================
FROM python:3.13-slim AS builder

# Avoid interactive prompts during package install
ENV DEBIAN_FRONTEND=noninteractive

# ---- System dependencies for WeasyPrint (pango, cairo, gdk-pixbuf, fonts) ----
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpango1.0-dev \
    shared-mime-info \
    fonts-liberation \
    fonts-dejavu-core \
    curl \
    gnupg \
    # Chromium deps for puppeteer (mermaid-cli uses puppeteer)
    chromium \
    && rm -rf /var/lib/apt/lists/*

# ---- Node.js (LTS) via NodeSource ----
RUN curl -fsSL https://deb.nodesource.com/setup_22.x | bash - \
    && apt-get install -y --no-install-recommends nodejs \
    && rm -rf /var/lib/apt/lists/*

# ---- mermaid-cli (mmdc) ----
RUN npm install -g @mermaid-js/mermaid-cli

# Tell puppeteer to use system Chromium instead of downloading its own
ENV PUPPETEER_EXECUTABLE_PATH=/usr/bin/chromium
ENV PUPPETEER_SKIP_CHROMIUM_DOWNLOAD=true
ENV PUPPETEER_CONFIG=/root/.puppeteerrc.json
ENV CHROMIUM_FLAGS="--no-sandbox --disable-gpu --disable-dev-shm-usage"

# Puppeteer config so mmdc uses system Chromium with required flags
RUN mkdir -p /root && echo '{ \
    "executablePath": "/usr/bin/chromium", \
    "args": ["--no-sandbox", "--disable-gpu", "--disable-dev-shm-usage", "--disable-setuid-sandbox"] \
}' > /root/.puppeteerrc.json

# ---- Python dependencies ----
COPY requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt

# =============================================================================
# Stage 2: Runtime image (copy only what we need)
# =============================================================================
FROM python:3.13-slim

ENV DEBIAN_FRONTEND=noninteractive

# Runtime system libraries (no -dev packages)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpango-1.0-0 \
    libpangocairo-1.0-0 \
    shared-mime-info \
    fonts-liberation \
    fonts-dejavu-core \
    chromium \
    curl \
    gnupg \
    && rm -rf /var/lib/apt/lists/*

# Node.js runtime
RUN curl -fsSL https://deb.nodesource.com/setup_22.x | bash - \
    && apt-get install -y --no-install-recommends nodejs \
    && rm -rf /var/lib/apt/lists/*

# Copy Python packages from builder
COPY --from=builder /usr/local/lib/python3.13/site-packages /usr/local/lib/python3.13/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copy global node_modules (mmdc) from builder
COPY --from=builder /usr/lib/node_modules /usr/lib/node_modules

RUN ln -sf /usr/lib/node_modules/@mermaid-js/mermaid-cli/src/cli.js /usr/local/bin/mmdc \
    && chmod +x /usr/local/bin/mmdc 2>/dev/null || true

# Puppeteer / Chromium config
ENV PUPPETEER_EXECUTABLE_PATH=/usr/bin/chromium
ENV PUPPETEER_SKIP_CHROMIUM_DOWNLOAD=true
ENV PUPPETEER_CONFIG=/root/.puppeteerrc.json
COPY --from=builder /root/.puppeteerrc.json /root/.puppeteerrc.json

# ---- Application code ----
WORKDIR /workspace

COPY build_pdf.py .
COPY templates/ templates/
COPY mkdocs.yml .

# Default: docs are mounted at /workspace/docs, output at /workspace/output
# These can be overridden via docker run args or pipeline variables
ENV INPUT_DIR=/workspace/docs
ENV OUTPUT_DIR=/workspace/output
ENV OUTPUT_FILENAME=document.pdf

COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

ENTRYPOINT ["/entrypoint.sh"]
