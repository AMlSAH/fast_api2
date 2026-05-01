from fastapi import FastAPI, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import or_
from sqlalchemy.exc import IntegrityError
import models, schemas, auth
from database import engine, SessionLocal, Base

Base.metadata.create_all(bind=engine)

app = FastAPI()

@app.on_event("startup")
def startup():
    db = SessionLocal()
    if not db.query(models.User).filter(models.User.username == "admin").first():
        admin_user = models.User(
            username="admin",
            hashed_password=auth.get_password_hash("secret"),
            group="admin"
        )
        db.add(admin_user)
        db.commit()
    db.close()

@app.post("/login", response_model=schemas.Token)
def login(data: schemas.LoginData, db: Session = Depends(auth.get_db)):
    user = db.query(models.User).filter(models.User.username == data.username).first()
    if not user or not auth.verify_password(data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Неверное имя пользователя или пароль",
        )
    access_token = auth.create_access_token(
        data={"sub": str(user.id), "group": user.group}
    )
    return {"access_token": access_token, "token_type": "bearer"}

@app.post("/user", response_model=schemas.UserOut, status_code=status.HTTP_201_CREATED)
def create_user(user_data: schemas.UserCreate, db: Session = Depends(auth.get_db)):
    existing = db.query(models.User).filter(models.User.username == user_data.username).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Пользователь с таким именем уже существует",
        )
    if user_data.group not in ("user", "admin"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Группа должна быть 'user' или 'admin'",
        )
    hashed = auth.get_password_hash(user_data.password)
    new_user = models.User(
        username=user_data.username,
        hashed_password=hashed,
        group=user_data.group
    )
    db.add(new_user)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Пользователь с таким именем уже существует",
        )
    db.refresh(new_user)
    return new_user

@app.get("/user/{user_id}", response_model=schemas.UserOut)
def get_user(user_id: int, db: Session = Depends(auth.get_db)):
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Пользователь не найден")
    return user

@app.patch("/user/{user_id}", response_model=schemas.UserOut)
def update_user(
    user_id: int,
    updates: schemas.UserUpdate,
    db: Session = Depends(auth.get_db),
    current_user: models.User = Depends(auth.get_current_user)
):
    if current_user.id != user_id and current_user.group != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Вы можете редактировать только свой профиль",
        )
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Пользователь не найден")
    if updates.username is not None:
        if db.query(models.User).filter(models.User.username == updates.username, models.User.id != user_id).first():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Пользователь с таким именем уже существует",
            )
        user.username = updates.username
    if updates.password is not None:
        user.hashed_password = auth.get_password_hash(updates.password)
    if updates.group is not None:
        if current_user.group != "admin":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Только администратор может изменять группу пользователя",
            )
        if updates.group not in ("user", "admin"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Группа должна быть 'user' или 'admin'",
            )
        user.group = updates.group
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Пользователь с таким именем уже существует",
        )
    db.refresh(user)
    return user

@app.delete("/user/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_user(
    user_id: int,
    db: Session = Depends(auth.get_db),
    current_user: models.User = Depends(auth.get_current_user)
):
    if current_user.id != user_id and current_user.group != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Вы можете удалить только свой аккаунт",
        )
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Пользователь не найден")
    db.delete(user)
    db.commit()
    return

@app.post("/advertisement", response_model=schemas.AdvertisementOut, status_code=status.HTTP_201_CREATED)
def create_advertisement(
    ad: schemas.AdvertisementCreate,
    db: Session = Depends(auth.get_db),
    current_user: models.User = Depends(auth.get_current_user)
):
    new_ad = models.Advertisement(**ad.model_dump(), owner_id=current_user.id)
    db.add(new_ad)
    db.commit()
    db.refresh(new_ad)
    return new_ad

@app.get("/advertisement/{ad_id}", response_model=schemas.AdvertisementOut)
def get_advertisement(ad_id: int, db: Session = Depends(auth.get_db)):
    ad = db.query(models.Advertisement).filter(models.Advertisement.id == ad_id).first()
    if not ad:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Объявление не найдено")
    return ad

@app.get("/advertisement", response_model=list[schemas.AdvertisementOut])
def search_advertisements(
    title: str = Query(None),
    description: str = Query(None),
    db: Session = Depends(auth.get_db)
):
    query = db.query(models.Advertisement)
    filters = []
    if title:
        filters.append(models.Advertisement.title.contains(title))
    if description:
        filters.append(models.Advertisement.description.contains(description))
    if filters:
        query = query.filter(or_(*filters))
    ads = query.all()
    return ads

@app.patch("/advertisement/{ad_id}", response_model=schemas.AdvertisementOut)
def update_advertisement(
    ad_id: int,
    updates: schemas.AdvertisementUpdate,
    db: Session = Depends(auth.get_db),
    current_user: models.User = Depends(auth.get_current_user)
):
    ad = db.query(models.Advertisement).filter(models.Advertisement.id == ad_id).first()
    if not ad:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Объявление не найдено")
    if current_user.id != ad.owner_id and current_user.group != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Вы не являетесь владельцем объявления")
    if updates.title is not None:
        ad.title = updates.title
    if updates.description is not None:
        ad.description = updates.description
    db.commit()
    db.refresh(ad)
    return ad

@app.delete("/advertisement/{ad_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_advertisement(
    ad_id: int,
    db: Session = Depends(auth.get_db),
    current_user: models.User = Depends(auth.get_current_user)
):
    ad = db.query(models.Advertisement).filter(models.Advertisement.id == ad_id).first()
    if not ad:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Объявление не найдено")
    if current_user.id != ad.owner_id and current_user.group != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Вы не являетесь владельцем объявления")
    db.delete(ad)
    db.commit()
    return
