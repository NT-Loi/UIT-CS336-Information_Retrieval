# Video Retrieval System

## How It Works

1.  **Data Ingestion**:
    -   Video metadata (title, description, etc.) from `.json` files is indexed into an Elasticsearch index.
    -   Pre-computed CLIP feature vectors (`.npy` files) for video keyframes are inserted into a Milvus collection.
2.  **Search Execution**:
    -   A user's text query is sent directly to Elasticsearch for keyword matching.
    -   The same text query is encoded into a vector by the CLIP model and used to find semantically similar keyframes in Milvus.
3.  **Result Fusion**:
    -   The ranked lists of videos from Elasticsearch and Milvus are combined using RRF. This produces a final, unified ranking that leverages both keyword relevance and semantic context.

## Data Tree

```
├── 📁 retrievers/
│   ├── 🐍 __init__.py
│   ├── 🐍 es_retriever.py
│   └── 🐍 milvus_retriever.py
├── 📁 static/
│   ├── 📄 script.js
│   └── 🎨 style.css
├── 📁 templates/
│   └── 🌐 index.html
├── 📁 utils/
│   ├── 🐍 __init__.py
│   ├── 🐍 ranker.py
│   └── 🐍 text_encoder.py
├── 📖 README.md
├── 🐍 app.py
├── 🐍 config.py
├── ⚙️ docker-compose.yml
├── 🐍 ingest_data.py
├── 🐍 ocr.py
├── 📄 requirements.txt
├── 🐍 retrieval_system.py
└── 📋 system.log
```

## Setup and Usage

### 1. Configure the Environment

Create a `config.py` file and populate it with the necessary paths and settings.

### 2. Start Services

```bash
docker compose up -d
```

### 3. Install Python Dependencies

```bash
pip install -r requirements.txt
```

### 5. Run the System
To ingest data for the first time, please set 're_ingest'=True.

```bash
python app.py
```