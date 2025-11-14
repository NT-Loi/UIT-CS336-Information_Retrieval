# Video Retrieval System

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