import json
import os
from pymongo import MongoClient

# 1. Carregar os links do ficheiro JSON antigo
JSON_FILE = "links.json"

if os.path.exists(JSON_FILE):
    with open(JSON_FILE, "r", encoding="utf-8") as f:
        old_links = json.load(f)

    # 2. Conectar ao MongoDB (insira a sua URI)
    MONGO_URI = "SUA_MONGO_URI_AQUI"
    client = MongoClient(MONGO_URI)
    db = client["sincplan_db"]
    collection = db["links"]

    # 3. Guardar os dados na empresa desejada (ex: AVEP)
    collection.update_one(
        {"company_id": "AVEP"},
        {"$set": {"company_id": "AVEP", "links": old_links}},
        upsert=True
    )

    print("✅ Dados do JSON migrados para o MongoDB com sucesso!")