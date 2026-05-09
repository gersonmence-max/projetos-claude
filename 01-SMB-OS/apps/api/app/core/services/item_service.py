from typing import List
from app.db.models.item import Item
from app.db.base import Session


class ItemService:
    def __init__(self, db: Session):
        self.db = db

    def criar_item(self, nome: str, quantidade: int):
        item = Item(nome=nome, quantidade=quantidade)
        self.db.add(item)
        self.db.commit()
        return item

    def baixa_item(self, item_id: uuid.UUID, quantidade: int):
        item = self.db.query(Item).filter(Item.id == item_id).first()
        if item:
            item.quantidade -= quantidade
            self.db.commit()
        return item