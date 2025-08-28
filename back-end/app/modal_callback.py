from fastapi import APIRouter, Request

router = APIRouter()

@router.post("/modal-callback")
async def modal_callback(request: Request):
    data = await request.json()
    print("Modal result:", data)
    return {"status": "received"}
