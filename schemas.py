from pydantic import BaseModel
from typing import Optional
from datetime import datetime

# ==========================================
# --- USER SCHEMAS ---
# ==========================================
class UserBase(BaseModel):
    username: str
    expo_push_token: Optional[str] = None
    avatar: str = "User"  # <-- The crucial fix for the leaderboard!

class UserCreate(BaseModel):
    username: str
    expo_push_token: Optional[str] = None

class UserResponse(UserBase):
    id: int
    current_streak: int
    total_saved: float

    class Config:
        from_attributes = True

# ==========================================
# --- VAULT SCHEMAS ---
# ==========================================
class VaultBase(BaseModel):
    title: str
    target: float
    owner_id: int

class VaultCreate(VaultBase):
    pass

class VaultResponse(VaultBase):
    id: int
    balance: float
    is_completed: bool

    class Config:
        from_attributes = True

# ==========================================
# --- TRANSACTION SCHEMAS ---
# ==========================================
class TransactionBase(BaseModel):
    amount: float
    type: str  # 'deposit' or 'withdraw'
    user_id: int
    vault_id: int

class TransactionCreate(TransactionBase):
    pass

class TransactionResponse(TransactionBase):
    id: int
    timestamp: datetime

    class Config:
        from_attributes = True