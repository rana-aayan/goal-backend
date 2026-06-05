from pydantic import BaseModel
from typing import Optional

# Base properties for a user
class UserBase(BaseModel):
    username: str
    expo_push_token: Optional[str] = None

# What we require when creating a user
class UserCreate(UserBase):
    pass

# What the API returns when someone requests user data
class UserResponse(UserBase):
    id: int
    current_streak: int
    total_saved: float
    avatar: str = "User"  # <--- We added the avatar field right here

    # This tells Pydantic it's okay to read data directly from our SQLAlchemy database models
    class Config:
        from_attributes = True

from datetime import datetime

# --- VAULT SCHEMAS ---
class VaultBase(BaseModel):
    title: str
    target: float

class VaultCreate(VaultBase):
    owner_id: int

class VaultResponse(VaultBase):
    id: int
    balance: float
    is_completed: bool
    owner_id: int

    class Config:
        from_attributes = True

# --- TRANSACTION SCHEMAS ---
class TransactionBase(BaseModel):
    amount: float
    type: str  # 'deposit' or 'withdraw'

class TransactionCreate(TransactionBase):
    user_id: int
    vault_id: int

class TransactionResponse(TransactionBase):
    id: int
    timestamp: datetime
    user_id: int
    vault_id: int

    class Config:
        from_attributes = True