from typing import List
from app.db.models.estoque import Estoque
from app.db.models.composicao import Composicao
from app.db.models.item import Item
from app.db.base import Session


class EstoqueService:
    def __init__(self, db: Session):
        self.db = db

    def criar_estoque(self, nome: str, quantidade: int):
        estoque = Estoque(nome=nome, quantidade=quantidade)
        self.db.add(estoque)
        self.db.commit()
        return estoque

    def criar_composicao(self, estoque_id: uuid.UUID, item_id: uuid.UUID, quantidade: int):
        composicao = Composicao(estoque_id=estoque_id, item_id=item_id, quantidade=quantidade)
        self.db.add(composicao)
        self.db.commit()
        return composicao

    def criar_item(self, nome: str, quantidade: int):
        item = Item(nome=nome, quantidade=quantidade)
        self.db.add(item)
        self.db.commit()
        return item

    def baixa_estoque(self, estoque_id: uuid.UUID, quantidade: int):
        estoque = self.db.query(Estoque).filter(Estoque.id == estoque_id).first()
        if estoque:
            estoque.quantidade -= quantidade
            self.db.commit()
        return estoque

    def baixa_composicao(self, composicao_id: uuid.UUID, quantidade: int):
        composicao = self.db.query(Composicao).filter(Composicao.id == composicao_id).first()
        if composicao:
            composicao.quantidade -= quantidade
            self.db.commit()
        return composicao

    def baixa_item(self, item_id: uuid.UUID, quantidade: int):
        item = self.db.query(Item).filter(Item.id == item_id).first()
        if item:
            item.quantidade -= quantidade
            self.db.commit()
        return item