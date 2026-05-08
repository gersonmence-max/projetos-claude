# backend/models.py
from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, Text
from sqlalchemy.sql import func
from database import Base


class Property(Base):
    __tablename__ = "properties"

    id = Column(Integer, primary_key=True, index=True)
    source = Column(String, nullable=False)          # "zillow" | "realtor"
    state = Column(String, nullable=False)           # "AL" | "AR"
    county = Column(String)
    address = Column(String)
    lat = Column(Float)
    lng = Column(Float)
    price = Column(Float)
    acres = Column(Float)
    price_per_acre = Column(Float)
    avg_price_per_acre = Column(Float)
    discount_pct = Column(Float)
    fema_zone = Column(String)
    has_road_access = Column(Boolean)
    utilities_available = Column(Boolean)
    zoning = Column(String)
    score = Column(Float)
    ai_analysis = Column(Text)                       # JSON string
    listing_url = Column(String, unique=True, index=True)
    parcel_id = Column(String, nullable=True)          # ID da parcela no condado
    sale_date = Column(String, nullable=True)           # "YYYY-MM-DD" — data do leilão
    scraped_at = Column(DateTime, nullable=False, server_default=func.now())
    passed_filters = Column(Boolean, default=False)
    population = Column(Integer, nullable=True)
    median_hh_income = Column(Float, nullable=True)
    investment_type = Column(String, nullable=True)   # "flip", "buy_hold", "avoid"
    risk_level = Column(String, nullable=True)          # "low", "medium", "high"
    risk_flags = Column(Text, nullable=True)            # JSON list of strings
    classification = Column(String, nullable=True)  # "FORTE", "MODERADO", "FRACO", "EVITAR"


class PipelineRun(Base):
    __tablename__ = "pipeline_runs"

    id = Column(Integer, primary_key=True, index=True)
    started_at = Column(DateTime, server_default=func.now())
    finished_at = Column(DateTime, nullable=True)
    status = Column(String, default="rodando")       # rodando | concluído | erro
    scraped = Column(Integer, default=0)
    enriched = Column(Integer, default=0)
    filtered = Column(Integer, default=0)
    scored = Column(Integer, default=0)
    error_msg = Column(Text, nullable=True)
