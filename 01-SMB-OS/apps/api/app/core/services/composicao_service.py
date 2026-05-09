from typing import List
from app.db.models.composicao import Composicao
from app.db.base import Session


class ComposicaoService:
    def __init__(self, db: Session):
        self.db = db

    def criar_composicao(self, estoque_id: uuid.UUID, item_id: uuid.UUID, quantidade: int):
        composicao = Composicao(estoque_id=estoque_id, item_id=item_id, quantidade=quantidade)
        self.db.add(composicao)
        self.db.commit()
        return composicao

    def baixa_composicao(self, composicao_id: uuid.UUID, quantidade: int):
        composicao = self.db.query(Composicao).filter(Composicao.id == composicao_id).first()
        if composicao:
            composicao.quantidade -= quantidade
            self.db.commit()
        return composicao