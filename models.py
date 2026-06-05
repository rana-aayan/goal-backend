from sqlalchemy import Column, Integer, String, Float, Boolean, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from datetime import datetime
from database import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    expo_push_token = Column(String, nullable=True) # For social notifications
    current_streak = Column(Integer, default=0)
    total_saved = Column(Float, default=0.0)
    avatar = Column(String, default="User")
    vaults = relationship("Vault", back_populates="owner")
    transactions = relationship("Transaction", back_populates="user")

class Vault(Base):
    __tablename__ = "vaults"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, index=True)
    target = Column(Float)
    balance = Column(Float, default=0.0)
    is_completed = Column(Boolean, default=False)
    owner_id = Column(Integer, ForeignKey("users.id"))

    owner = relationship("User", back_populates="vaults")
    transactions = relationship("Transaction", back_populates="vault")

class Transaction(Base):
    __tablename__ = "transactions"

    id = Column(Integer, primary_key=True, index=True)
    amount = Column(Float)
    type = Column(String) # 'deposit' or 'withdraw'
    timestamp = Column(DateTime, default=datetime.utcnow)
    
    user_id = Column(Integer, ForeignKey("users.id"))
    vault_id = Column(Integer, ForeignKey("vaults.id"))

    user = relationship("User", back_populates="transactions")
    vault = relationship("Vault", back_populates="transactions")