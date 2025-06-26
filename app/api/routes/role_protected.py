from fastapi import APIRouter, Depends
from app.deps.roles import get_current_user_role

router = APIRouter()

@router.get("/manager-only")
def manager_action(role: str = Depends(get_current_user_role)):
    if role != "manager":
        raise HTTPException(status_code=403, detail="Only managers allowed")
    return {"message": "Manager access granted"}

@router.get("/admin-only")
def admin_action(role: str = Depends(get_current_user_role)):
    if role != "admin":
        raise HTTPException(status_code=403, detail="Only admins allowed")
    return {"message": "Admin access granted"}
