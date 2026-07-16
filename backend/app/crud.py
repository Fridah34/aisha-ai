from sqlalchemy.orm import Session
from app.models import User
from typing import Optional

#==================================================================================
#                       USER & AUTHENTICATION OPERATIONS
#==================================================================================

#=========CREATE OPERATIONS==========

def create_user(
        db: Session,
        email: str,
        name: str,
        business_name: str,
        hashed_password: str,
) -> User:
    new_user = User(
        email=email,
        name=name,
        business_name=business_name,
        hashed_password=hashed_password
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user

#========== READ OPERATIONS==========

def get_user_by_email(db: Session, email: str) -> Optional[User]:
    return db.query(User).filter(User.email == email).first()

def get_all_users(db:Session,skip: int = 0, limit: int = 100) -> list[User]:
    return db.query(User).offset(skip).limit(limit).all()

#========== UPDATE OPERATIONS==========

def update_user(
        db: Session,
        user_id: int,
        **kwargs
)-> Optional[User]:
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        return None
    for key, value in kwargs.items():
        if hasattr(user, key):
            setattr(user, key, value)
    db.commit()
    db.refresh(user)
    return user     

#========== DELETE OPERATIONS==========

def delete_user(db: Session, user_id: int) -> Optional[User]:
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        return None
    db.delete(user)
    db.commit()
    return user

#=========HELPER OPERATIONS==========

def user_exists(db:Session,email:str) -> bool:
    return db.query(User).filter(User.email == email).first() is not None

def get_active_users(db: Session) -> list[User]:
    return db.query(User).filter(User.is_active).all()