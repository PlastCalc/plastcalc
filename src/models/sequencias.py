from datetime import datetime
from src.data.storage_json import load, save

DB_SEQ = "sequencias"

def next_doc(prefixo: str, ano: int | None = None) -> str:
    if ano is None:
        ano = datetime.now().year

    db = load(DB_SEQ)  # ex.: {"ORC-2026": 12}
    key = f"{prefixo}-{ano}"
    atual = int(db.get(key, 0)) + 1
    db[key] = atual
    save(DB_SEQ, db)

    return f"{prefixo}-{ano}-{atual:04d}"
