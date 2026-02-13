#Centraliza todas as configurações do projeto

import os
from dotenv import load_dotenv

load_dotenv()

PIPEDRIVE_API_TOKEN = os.getenv("PIPEDRIVE_API_TOKEN")
PIPEDRIVE_BASE_URL = os.getenv("PIPEDRIVE_BASE_URL")

GCP_PROJECT_ID = os.getenv("GCP_PROJECT_ID")
BQ_DATASET = os.getenv("BQ_DATASET")

if not PIPEDRIVE_API_TOKEN:
    raise ValueError("Faltou PIPEDRIVE_API_TOKEN no .env")
if not GCP_PROJECT_ID:
    raise ValueError("Faltou GCP_PROJECT_ID no .env")
