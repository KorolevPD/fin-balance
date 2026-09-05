from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routers import auth, families, transactions, uploads

app = FastAPI(title="FinBalance API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(uploads.router, prefix="/api")

@app.get("/")
async def root():
    return {"message": "FinBalance API"}

@app.get("/health")
async def health():
    return {"status": "healthy"}

app.include_router(auth.router, prefix="/api")
app.include_router(families.router, prefix="/api")
app.include_router(transactions.router, prefix="/api")
