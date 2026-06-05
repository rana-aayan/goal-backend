from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import datetime, date, timedelta
from pydantic import BaseModel
import models, schemas
from database import engine, SessionLocal

# Create tables in Supabase
models.Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Goal Backend",
    description="The engine powering the social saving network.",
    version="1.0.0"
)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@app.get("/")
def health_check():
    return {"status": "online", "message": "API is live."}

# ==========================================
# --- AUTH & USER ENDPOINTS ---
# ==========================================

class LoginRequest(BaseModel):
    username: str

class ProfileUpdate(BaseModel):
    username: str
    avatar: str

@app.post("/login/")
def login_user(req: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.username == req.username).first()
    if not user:
        raise HTTPException(status_code=404, detail="Username not found. Please register.")
    return user

@app.post("/users/", response_model=schemas.UserResponse)
def create_user(user: schemas.UserCreate, db: Session = Depends(get_db)):
    existing_user = db.query(models.User).filter(models.User.username == user.username).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="Username already taken.")
    
    new_user = models.User(username=user.username, expo_push_token=user.expo_push_token)
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user

@app.put("/users/{user_id}/profile")
def update_profile(user_id: int, req: ProfileUpdate, db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Prevent stealing someone else's username
    if req.username != user.username:
        conflict = db.query(models.User).filter(models.User.username == req.username).first()
        if conflict:
            raise HTTPException(status_code=400, detail="Username already taken.")
            
    user.username = req.username
    user.avatar = req.avatar
    db.commit()
    db.refresh(user)
    return user

@app.get("/users/{target_user_id}/profile")
def get_user_profile(target_user_id: int, db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.id == target_user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    vaults = db.query(models.Vault).filter(models.Vault.owner_id == target_user_id).all()
    vault_data = [{"title": v.title, "target": v.target, "balance": v.balance, "is_completed": v.balance >= v.target} for v in vaults]
        
    return {
        "username": user.username,
        "avatar": getattr(user, 'avatar', 'User'),
        "current_streak": user.current_streak,
        "total_saved": user.total_saved,
        "vaults": vault_data
    }

# ==========================================
# --- LEADERBOARD & VAULTS ---
# ==========================================

@app.get("/leaderboard/", response_model=list[schemas.UserResponse])
def get_leaderboard(db: Session = Depends(get_db)):
    top_users = db.query(models.User).order_by(models.User.total_saved.desc()).limit(10).all()
    today_date = date.today()
    for user in top_users:
        last_tx = db.query(models.Transaction).filter(
            models.Transaction.user_id == user.id,
            models.Transaction.type == 'deposit',
            models.Transaction.amount >= 10
        ).order_by(models.Transaction.timestamp.desc()).first()
        
        if last_tx and (today_date - last_tx.timestamp.date()).days > 1:
            user.current_streak = 0
            db.commit()
    return top_users

@app.post("/vaults/", response_model=schemas.VaultResponse)
def create_vault(vault: schemas.VaultCreate, db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.id == vault.owner_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found.")
    new_vault = models.Vault(**vault.model_dump())
    db.add(new_vault)
    db.commit()
    db.refresh(new_vault)
    return new_vault

# ==========================================
# --- TRANSACTION ENGINE ---
# ==========================================

@app.post("/transactions/", response_model=schemas.TransactionResponse)
def create_transaction(transaction: schemas.TransactionCreate, db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.id == transaction.user_id).first()
    vault = db.query(models.Vault).filter(models.Vault.id == transaction.vault_id).first()

    if not user or not vault:
        raise HTTPException(status_code=404, detail="User or Vault not found.")

    if transaction.type == 'deposit':
        vault.balance += transaction.amount
        user.total_saved += transaction.amount
        
        if transaction.amount >= 10:
            today_date = date.today()
            last_deposit = db.query(models.Transaction).filter(
                models.Transaction.user_id == user.id,
                models.Transaction.type == 'deposit',
                models.Transaction.amount >= 10
            ).order_by(models.Transaction.timestamp.desc()).first()

            if last_deposit:
                days_difference = (today_date - last_deposit.timestamp.date()).days
                if days_difference == 1:
                    user.current_streak += 1
                elif days_difference > 1:
                    user.current_streak = 1
            else:
                user.current_streak = 1
            
    elif transaction.type == 'withdraw':
        if vault.balance < transaction.amount:
            raise HTTPException(status_code=400, detail="Insufficient vault funds.")
        vault.balance -= transaction.amount
        user.total_saved -= transaction.amount

    if vault.balance >= vault.target:
        vault.is_completed = True

    new_transaction = models.Transaction(**transaction.model_dump())
    db.add(new_transaction)
    db.commit()
    db.refresh(new_transaction)
    return new_transaction