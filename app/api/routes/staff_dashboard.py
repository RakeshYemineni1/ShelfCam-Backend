# app/api/routes/staff_dashboard.py

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.database.db import get_db
from app.deps.roles import get_current_user_role
from app.models.staff_assignment import StaffAssignment
from app.schemas.response import AssignmentStatusResponse

router = APIRouter()

@router.get("/me/assignment", response_model=AssignmentStatusResponse)
def get_my_assignment(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user_role)
):
    assignment = db.query(StaffAssignment).filter_by(employee_id=current_user.employee_id).first()

    if assignment:
        return AssignmentStatusResponse(
            assigned=True,
            shelf_id=assignment.shelf_id,
            notes=assignment.notes
        )
    return AssignmentStatusResponse(
        assigned=False,
        shelf_id=None,
        notes=None
    )
