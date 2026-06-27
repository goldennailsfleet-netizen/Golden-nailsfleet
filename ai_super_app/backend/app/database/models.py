"""
Database Models - SQLAlchemy
"""
from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime, Float, Boolean, ForeignKey, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, sessionmaker
from datetime import datetime

Base = declarative_base()


class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, index=True)
    email = Column(String(100), unique=True, index=True)
    hashed_password = Column(String(255))
    is_active = Column(Boolean, default=True)
    is_admin = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    preferred_model = Column(String(50), default="auto")
    prefer_offline = Column(Boolean, default=False)
    default_language = Column(String(10), default="ar")
    chats = relationship("Chat", back_populates="user")
    generations = relationship("Generation", back_populates="user")


class Chat(Base):
    __tablename__ = "chats"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    title = Column(String(200))
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    user = relationship("User", back_populates="chats")
    messages = relationship("Message", back_populates="chat")


class Message(Base):
    __tablename__ = "messages"
    id = Column(Integer, primary_key=True, index=True)
    chat_id = Column(Integer, ForeignKey("chats.id"))
    role = Column(String(20))
    content = Column(Text)
    model_used = Column(String(50))
    tokens_used = Column(Integer, default=0)
    latency_ms = Column(Float)
    created_at = Column(DateTime, default=datetime.utcnow)
    chat = relationship("Chat", back_populates="messages")


class Generation(Base):
    __tablename__ = "generations"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    type = Column(String(20))
    prompt = Column(Text)
    provider = Column(String(50))
    result_url = Column(String(500))
    result_data = Column(Text)
    parameters = Column(JSON)
    status = Column(String(20), default="pending")
    generation_time = Column(Float)
    created_at = Column(DateTime, default=datetime.utcnow)
    user = relationship("User", back_populates="generations")


class WebAccess(Base):
    __tablename__ = "web_accesses"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    url = Column(String(500))
    proxy_used = Column(String(100))
    latency_ms = Column(Float)
    content_type = Column(String(50))
    extracted_data = Column(JSON)
    created_at = Column(DateTime, default=datetime.utcnow)


class VPNUsage(Base):
    __tablename__ = "vpn_usage"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    proxy_host = Column(String(100))
    proxy_country = Column(String(10))
    target_url = Column(String(500))
    success = Column(Boolean)
    latency_ms = Column(Float)
    created_at = Column(DateTime, default=datetime.utcnow)


class ModelPerformanceLog(Base):
    __tablename__ = "model_performance"
    id = Column(Integer, primary_key=True, index=True)
    model_name = Column(String(50))
    query_type = Column(String(50))
    latency_ms = Column(Float)
    success = Column(Boolean)
    tokens_input = Column(Integer)
    tokens_output = Column(Integer)
    user_rating = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


from app.config import settings

engine = create_engine(settings.DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def create_tables():
    Base.metadata.create_all(bind=engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
