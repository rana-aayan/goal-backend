from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.orm import Session
import models, schemas
from database import engine, SessionLocal
from datetime import datetime, date, timedelta

# Create tables
models.Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Goals Vault Backend",
    description="The engine powering the social saving network.",
    version="1.0.0"
)

# Dependency: Opens a database session for a request, then closes it when done
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@app.get("/")
def health_check():
    return {"status": "online", "message": "API is live."}

# --- USER ENDPOINTS ---

@app.post("/users/", response_model=schemas.UserResponse)
def create_user(user: schemas.UserCreate, db: Session = Depends(get_db)):
    # Check if username is taken
    existing_user = db.query(models.User).filter(models.User.username == user.username).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="Username already taken.")
    
    # Create the new user
    new_user = models.User(username=user.username, expo_push_token=user.expo_push_token)
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user



from fastapi import HTTPException

# --- VAULT ENDPOINTS ---

@app.post("/vaults/", response_model=schemas.VaultResponse)
def create_vault(vault: schemas.VaultCreate, db: Session = Depends(get_db)):
    # Verify the user actually exists first
    user = db.query(models.User).filter(models.User.id == vault.owner_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found.")

    new_vault = models.Vault(**vault.model_dump())
    db.add(new_vault)
    db.commit()
    db.refresh(new_vault)
    return new_vault

@app.get("/leaderboard/", response_model=list[schemas.UserResponse])
def get_leaderboard(db: Session = Depends(get_db)):
    top_users = db.query(models.User).order_by(models.User.total_saved.desc()).limit(10).all()
    
    # Active check: Reset streak to 0 if they haven't saved in over 48 hours
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

# --- TRANSACTION & STREAK ENGINE ---



@app.post("/transactions/", response_model=schemas.TransactionResponse)
def create_transaction(transaction: schemas.TransactionCreate, db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.id == transaction.user_id).first()
    vault = db.query(models.Vault).filter(models.Vault.id == transaction.vault_id).first()

    if not user or not vault:
        raise HTTPException(status_code=404, detail="User or Vault not found.")

    if transaction.type == 'deposit':
        vault.balance += transaction.amount
        user.total_saved += transaction.amount
        
        # --- SMART DAILY STREAK LOGIC ---
        if transaction.amount >= 10:
            today_date = date.today()
            
            # Find the user's last deposit of 10 PKR or more
            last_deposit = db.query(models.Transaction).filter(
                models.Transaction.user_id == user.id,
                models.Transaction.type == 'deposit',
                models.Transaction.amount >= 10
            ).order_by(models.Transaction.timestamp.desc()).first()

            if last_deposit:
                last_deposit_date = last_deposit.timestamp.date()
                days_difference = (today_date - last_deposit_date).days

                if days_difference == 1:
                    # Deposited yesterday! Increment streak
                    user.current_streak += 1
                elif days_difference > 1:
                    # Missed a day. Streak shatters and resets to 1
                    user.current_streak = 1
                # If days_difference == 0, they already deposited today; leave streak as is!
            else:
                # First time depositing ever
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

# --- PUBLIC PROFILE ENDPOINT ---

@app.get("/users/{target_user_id}/profile")
def get_user_profile(target_user_id: int, db: Session = Depends(get_db)):
    # 1. Fetch the user's core stats
    user = db.query(models.User).filter(models.User.id == target_user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # 2. Fetch all vaults belonging to this specific user
    vaults = db.query(models.Vault).filter(models.Vault.owner_id == target_user_id).all()
    
    # 3. Package the vaults into a clean, readable format for the app
    vault_data = []
    for v in vaults:
        vault_data.append({
            "title": v.title,
            "target": v.target,
            "balance": v.balance,
            "is_completed": v.balance >= v.target
        })
        
    # 4. Ship the bundled profile back to the phone
    return {
        "username": user.username,
        "current_streak": user.current_streak,
        "total_saved": user.total_saved,
        "vaults": vault_data
    }