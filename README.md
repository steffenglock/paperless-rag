# Paperless RAG

RAG-powered (Retrieval-Augmented Generation) semantic search and assistant for your Paperless-ngx documents. Ask questions about your archived documents and get precise answers with clickable source links.

## Features

- **Automated Sync:** Pulls new document metadata from Paperless-ngx automatically every hour.
- **Manual Sync:** Trigger an immediate sync directly from the chat UI with a single click.
- **Clickable Sources:** References used by the LLM display as cards under the response and link directly back to the original document inside Paperless-ngx.
- **Robust Security:** Masked API-Keys in the frontend prevent unintentional overwrites when changing model configurations.

## Setup & Configuration

1. Open the **Settings** page in the web user interface.
2. Configure your **Paperless-ngx** connection:
   - **URL:** The base URL of your Paperless-ngx instance (e.g., `http://192.168.178.153:8010`).
   - **API Token:** Your personal API access token generated in Paperless.
3. Configure your **Embeddings** and **LLM** providers (Supports OpenRouter, OpenAI, and Ollama).
4. Save the configuration and click **Sync** on the main dashboard to start your first background indexation.
