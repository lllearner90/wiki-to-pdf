# CI/CD Integration

Automating your PDF generation inside your CI/CD pipelines ensures your documentation is always up to date with your source code. 

**wiki-to-pdf** provides a built-in Dockerfile that is trivial to plug into Azure Pipelines, GitHub Actions, or GitLab CI.

## Azure Pipelines

An example `azure-pipelines.yml` is included in the project repository. It demonstrates how to build the Docker image and use it to publish the PDF as a build artifact.

### How It Works

The Azure Pipeline roughly performs the following steps:

1. **Builds and Pushes the Docker Image** natively to your Azure Container Registry (ACR).
2. **Executes the Container**, passing in the repository's source files as volumes.
3. **Extracts the PDF** from the output directory and publishes it as a pipeline artifact.

### Sample Configuration

```yaml
trigger:
  - main

pool:
  vmImage: 'ubuntu-latest'

steps:
- script: |
    echo "Building wiki-to-pdf Docker image..."
    # Uses the Docker@2 task to build and push to ACR
    # See azure-pipelines.yml for full implementation
  displayName: 'Build Docker Image'

- script: |
    echo "Generating PDF via Docker..."
    mkdir -p $(System.DefaultWorkingDirectory)/output
    
    docker run --rm \
      -v $(System.DefaultWorkingDirectory):/workspace/project \
      -v $(System.DefaultWorkingDirectory)/output:/workspace/output \
      -e PDF_TITLE="System Architecture" \
      -e PDF_AUTHOR="DevOps Team" \
      $(containerRegistry)/$(imageRepository):latest
  displayName: 'Generate PDF'

- task: PublishPipelineArtifact@1
  inputs:
    targetPath: '$(System.DefaultWorkingDirectory)/output/document.pdf'
    artifact: 'DocumentationPDF'
    publishLocation: 'pipeline'
  displayName: 'Publish PDF Artifact'
```

Once the pipeline succeeds, users can navigate to the **Artifacts** tab on the Azure DevOps build results page to download the latest PDF.

## GitHub Actions

A GitHub Actions workflow is also included in `.github/workflows/build-and-publish.yml`. 

### How It Works

1. **Builds and Pushes the Docker Image** to the GitHub Container Registry (`ghcr.io`).
2. **Executes the Container** using the newly built image to process your markdown.
3. **Uploads the PDF** as a GitHub Actions Artifact.

### Sample Configuration

```yaml
name: Build PDF and Publish Docker Image

on:
  push:
    branches:
      - main

env:
  REGISTRY: ghcr.io
  IMAGE_NAME: ${{ github.repository }}

jobs:
  build-and-publish:
    runs-on: ubuntu-latest
    permissions:
      contents: read
      packages: write
      
    steps:
      - uses: actions/checkout@v4

      - name: Log in to the Container registry
        uses: docker/login-action@v3
        with:
          registry: ${{ env.REGISTRY }}
          username: ${{ github.actor }}
          password: ${{ secrets.GITHUB_TOKEN }}

      - name: Build and push Docker image
        uses: docker/build-push-action@v5
        with:
          context: .
          push: true
          load: true
          tags: ${{ env.REGISTRY }}/${{ env.IMAGE_NAME }}:latest

      - name: Generate PDF via Docker
        run: |
          mkdir -p output
          docker run --rm \
            -v ${{ github.workspace }}:/workspace/project \
            -v ${{ github.workspace }}/output:/workspace/output \
            -e OUTPUT_FILENAME=Technical_Documentation.pdf \
            ${{ env.REGISTRY }}/${{ env.IMAGE_NAME }}:latest

      - name: Upload PDF Artifact
        uses: actions/upload-artifact@v4
        with:
          name: Documentation
          path: output/Technical_Documentation.pdf
```

When the action finishes, download your PDF directly from the **Artifacts** section at the bottom of the workflow run summary!

## GitLab CI

The exact same concept applies to **GitLab CI**. Simply replace the pipeline syntax with the native Docker steps for your chosen platform. Ensure the directory paths correctly point to your repository clone (`$CI_PROJECT_DIR`).