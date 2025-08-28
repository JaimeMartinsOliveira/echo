from fastapi import FastAPI
from app.routes import router as routes


app = FastAPI(title="Echo - Backend")
app.include_router(routes)


@app.get("/")
async def root():
return {"status": "ok", "service": "Echo backend"}