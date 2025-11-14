# Video Retrieval System

## Setup and Usage

### 1. Configure the Environment

Please make sure you have installed `mongodb`. Detailed intructions are provided here: [How to Install MongoDB on Ubuntu: A Step-by-Step Guide for Beginners](https://www.datacamp.com/tutorial/install-mongodb-on-ubuntu?utm_cid=19589720824&utm_aid=186331390789&utm_campaign=230119_1-ps-other~dsa~tofu_2-b2c_3-apac_4-prc_5-na_6-na_7-le_8-pdsh-go_9-nb-e_10-na_11-na&utm_loc=9222432-&utm_mtd=-c&utm_kw=&utm_source=google&utm_medium=paid_search&utm_content=ps-other~apac-en~dsa~tofu~tutorial~mongodb&gad_source=1&gad_campaignid=19589720824&gclid=CjwKCAiAoNbIBhB5EiwAZFbYGLG0dweUf1TYtepACWoxSKU_0KLUhpkxWlzyY_Xey--YQvLC22JYlhoCLRgQAvD_BwE)
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