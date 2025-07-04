from fastapi import FastAPI
from app.api.routes import auth
from app.database.db import Base, engine
from app.api.routes import auth, role_protected

Base.metadata.create_all(bind=engine)

app = FastAPI()

@app.get("/")
def root():
    return {"message": "ShelfCam API is live!"}

app.include_router(auth.router, prefix="/auth", tags=["auth"])
