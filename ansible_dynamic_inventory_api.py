import json

from pathlib import Path

from fastapi import FastAPI

app = FastAPI()


@app.get("/inventory")
def read_inventory():
    result = json.loads(Path("sample-inventory.json"))
    return result
