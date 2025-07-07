# ✅ Cleaned version of staff_assignment.py with only username used for employee display
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session, aliased
from sqlalchemy import and_, select
from typing import List, Optional
from datetime import datetime

from app.database.db import get_db
from app.models.staff_assignment import StaffAssignment, AssignmentHistory
from app.models.employee import Employee
from app.models.shelf import Shelf
from app.schemas.staff_assignment import (
    StaffAssignmentCreate, StaffAssignmentUpdate, StaffAssignmentResponse,
    AvailableStaffResponse, AssignmentHistoryResponse, AssignmentDashboardResponse
)
from app.schemas.shelf import ShelfWithAssignments
from app.core.auth import require_store_manager

router = APIRouter(prefix="/staff-assignments", tags=["staff-assignment"])

@router.get("/dashboard", response_model=AssignmentDashboardResponse)
def get_assignment_dashboard(db: Session = Depends(get_db), current_user: Employee = Depends(require_store_manager)):
    total_shelves = db.query(Shelf).count()
    active_shelves = db.query(Shelf).filter(Shelf.is_active == True).count()
    inactive_shelves = total_shelves - active_shelves

    total_assignments = db.query(StaffAssignment).count()
    active_assignments = db.query(StaffAssignment).filter(StaffAssignment.is_active == True).count()

    assigned_employee_ids = select(StaffAssignment.employee_id).filter(StaffAssignment.is_active == True)

    available_staff_count = db.query(Employee).filter(
        and_(Employee.role == "staff", Employee.is_active == True, ~Employee.employee_id.in_(assigned_employee_ids))
    ).count()

    shelves_with_assignments = []
    shelves = db.query(Shelf).filter(Shelf.is_active == True).all()

    for shelf in shelves:
        Staff = aliased(Employee)
        assignments = db.query(StaffAssignment).join(Staff, StaffAssignment.employee_id == Staff.employee_id).filter(
            and_(StaffAssignment.shelf_id == shelf.name, StaffAssignment.is_active == True, Staff.is_active == True)
        ).all()

        assigned_staff_names = [assignment.employee.username for assignment in assignments]

        shelf_data = ShelfWithAssignments(
            id=shelf.id,
            name=shelf.name,
            category=shelf.category.value if hasattr(shelf.category, 'value') else str(shelf.category),
            is_active=shelf.is_active,
            capacity=shelf.capacity,
            created_at=shelf.created_at,
            updated_at=shelf.updated_at,
            assigned_staff_count=len(assignments),
            assigned_staff=assigned_staff_names,
        )
        shelves_with_assignments.append(shelf_data)

    return AssignmentDashboardResponse(
        total_shelves=total_shelves,
        active_shelves=active_shelves,
        inactive_shelves=inactive_shelves,
        total_assignments=total_assignments,
        active_assignments=active_assignments,
        available_staff_count=available_staff_count,
        shelves_with_assignments=shelves_with_assignments
    )

@router.get("/available-staff", response_model=List[AvailableStaffResponse])
def get_available_staff(db: Session = Depends(get_db), current_user: Employee = Depends(require_store_manager)):
    assigned_employee_ids = select(StaffAssignment.employee_id).filter(StaffAssignment.is_active == True)

    available_staff = db.query(Employee).filter(
        and_(Employee.role == "staff", Employee.is_active == True, ~Employee.employee_id.in_(assigned_employee_ids))
    ).all()

    return [
        AvailableStaffResponse(
            id=emp.id,
            employee_id=emp.employee_id,
            username=emp.username,
            email=emp.email,
            phone=emp.phone,
            role=emp.role or "Staff"
        ) for emp in available_staff
    ]

@router.post("/assign", response_model=StaffAssignmentResponse, status_code=status.HTTP_201_CREATED)
def assign_staff_to_shelf(assignment_data: StaffAssignmentCreate, db: Session = Depends(get_db), current_user: Employee = Depends(require_store_manager)):
    employee = db.query(Employee).filter(
        and_(Employee.employee_id == assignment_data.employee_id, Employee.role == "staff", Employee.is_active == True)
    ).first()
    if not employee:
        raise HTTPException(status_code=404, detail="Active staff member not found")

    shelf = db.query(Shelf).filter(
        and_(Shelf.name == assignment_data.shelf_id, Shelf.is_active == True)
    ).first()
    if not shelf:
        raise HTTPException(status_code=404, detail="Active shelf not found")

    existing_assignment = db.query(StaffAssignment).filter(
        and_(StaffAssignment.employee_id == employee.employee_id, StaffAssignment.is_active == True)
    ).first()
    if existing_assignment:
        raise HTTPException(status_code=400, detail="Employee is already assigned to another shelf")

    assignment = StaffAssignment(
        employee_id=employee.employee_id,
        shelf_id=shelf.name,
        assigned_by=current_user.employee_id,
        notes=assignment_data.notes
    )
    db.add(assignment)
    db.commit()
    db.refresh(assignment)

    history = AssignmentHistory(
        employee_id=employee.employee_id,
        shelf_id=shelf.name,
        action="assigned",
        performed_by=current_user.employee_id,
        notes=assignment_data.notes
    )
    db.add(history)
    db.commit()

    return StaffAssignmentResponse(
        id=assignment.id,
        employee_id=assignment.employee_id,
        employee_name=employee.username,
        shelf_id=shelf.name,
        shelf_name=shelf.name,
        shelf_category=shelf.category.value if hasattr(shelf.category, 'value') else str(shelf.category),
        is_active=assignment.is_active,
        assigned_at=assignment.assigned_at,
        assigned_date=assignment.assigned_at,
        created_at=assignment.created_at,
        updated_at=assignment.updated_at,
        assigned_by=current_user.employee_id,
        assigned_by_name=current_user.username,
        notes=assignment.notes
    )

@router.get("/", response_model=List[StaffAssignmentResponse])
def get_all_assignments(
    db: Session = Depends(get_db),
    current_user: Employee = Depends(require_store_manager)
):
    # Aliases for joining the same table twice
    Staff = aliased(Employee)
    Manager = aliased(Employee)

    # Fetch everything needed
    query = (
        db.query(
            StaffAssignment.id,
            StaffAssignment.employee_id,
            StaffAssignment.shelf_id,
            StaffAssignment.is_active,
            StaffAssignment.assigned_at,
            StaffAssignment.created_at,
            StaffAssignment.updated_at,
            StaffAssignment.notes,
            StaffAssignment.assigned_by,
            Staff.username.label("employee_name"),
            Shelf.name.label("shelf_name"),
            Shelf.category.label("shelf_category"),
            Manager.username.label("assigned_by_name")
        )
        .join(Staff, Staff.employee_id == StaffAssignment.employee_id)
        .join(Shelf, Shelf.name == StaffAssignment.shelf_id)
        .join(Manager, Manager.employee_id == StaffAssignment.assigned_by)
    )

    rows = query.all()

    return [
        StaffAssignmentResponse(
            id=row.id,
            employee_id=row.employee_id,
            shelf_id=row.shelf_id,
            is_active=row.is_active,
            assigned_date=row.assigned_at,
            created_at=row.created_at,
            updated_at=row.updated_at,
            notes=row.notes,
            assigned_by=row.assigned_by,
            employee_name=row.employee_name,
            shelf_name=row.shelf_name,
            shelf_category=row.shelf_category.value if hasattr(row.shelf_category, 'value') else str(row.shelf_category),
            assigned_by_name=row.assigned_by_name
        )
        for row in rows
    ]

# @router.put("/{assignment_id}", response_model=StaffAssignmentResponse)
# def update_assignment(assignment_id: int, assignment_data: StaffAssignmentUpdate, db: Session = Depends(get_db), current_user: Employee = Depends(require_store_manager)):
#     assignment = db.query(StaffAssignment).filter(StaffAssignment.id == assignment_id).first()
#     if not assignment:
#         raise HTTPException(status_code=404, detail="Assignment not found")

#     update_data = assignment_data.model_dump(exclude_unset=True)
#     for field, value in update_data.items():
#         setattr(assignment, field, value)
#     db.commit()
#     db.refresh(assignment)

#     if 'is_active' in update_data and not update_data['is_active']:
#         history = AssignmentHistory(
#             employee_id=assignment.employee_id,
#             shelf_id=assignment.shelf_id,
#             action="unassigned",
#             performed_by=current_user.employee_id,
#             notes=assignment_data.notes
#         )
#         db.add(history)
#         db.commit()

#     manager = db.query(Employee).filter(Employee.employee_id == assignment.assigned_by).first()
#     return StaffAssignmentResponse(
#         id=assignment.id,
#         employee_id=assignment.employee_id,
#         shelf_id=assignment.shelf_id,
#         is_active=assignment.is_active,
#         assigned_at=assignment.assigned_at,
#         assigned_by=assignment.assigned_by,
#         notes=assignment.notes,
#         employee_name=assignment.employee.username,
#         shelf_name=assignment.shelf.name,
#         shelf_category=assignment.shelf.category.value if hasattr(assignment.shelf.category, 'value') else str(assignment.shelf.category),
#         assigned_by_name=manager.username if manager else "Unknown"
#     )

@router.delete("/{assignment_id}", status_code=204)
def unassign_staff(assignment_id: int, db: Session = Depends(get_db), current_user: Employee = Depends(require_store_manager)):
    assignment = db.query(StaffAssignment).filter(StaffAssignment.id == assignment_id).first()
    if not assignment:
        raise HTTPException(status_code=404, detail="Assignment not found")

    history = AssignmentHistory(
        employee_id=assignment.employee_id,
        shelf_id=assignment.shelf_id,
        action="unassigned",
        performed_by=current_user.employee_id,
        notes="Assignment deleted"
    )
    db.add(history)
    db.delete(assignment)
    db.commit()

# @router.get("/history", response_model=List[AssignmentHistoryResponse])
# def get_assignment_history(shelf_id: Optional[str] = None, limit: int = 100, db: Session = Depends(get_db), current_user: Employee = Depends(require_store_manager)):
#     query = db.query(AssignmentHistory)
#     if shelf_id:
#         query = query.filter(AssignmentHistory.shelf_id == shelf_id)

#     history = query.order_by(AssignmentHistory.action_date.desc()).limit(limit).all()

#     managers = {
#         r.performed_by: db.query(Employee).filter(Employee.employee_id == r.performed_by).first()
#         for r in history
#     }

#     # 🚀 Find matching assignment ID
#     def get_assignment_id(emp_id: str, shelf_id: str):
#         assignment = db.query(StaffAssignment).filter(
#             StaffAssignment.employee_id == emp_id,
#             StaffAssignment.shelf_id == shelf_id
#         ).first()
#         return assignment.id if assignment else None

#     return [
#         AssignmentHistoryResponse(
#             id=r.id,
#             assignment_id=get_assignment_id(r.employee_id, r.shelf_id),
#             created_by=r.performed_by,
#             timestamp=r.action_date,
#             employee_id=r.employee_id,
#             shelf_id=r.shelf_id,
#             action=r.action,
#             action_date=r.action_date,
#             performed_by=r.performed_by,
#             notes=r.notes,
#             employee_name=r.employee.username,
#             shelf_name=r.shelf.name,
#             manager_name=managers[r.performed_by].username if managers[r.performed_by] else "Unknown"
#         ) for r in history
#     ]


@router.post("/transfer/{assignment_id}", response_model=StaffAssignmentResponse)
def transfer_staff_to_different_shelf(assignment_id: int, new_shelf_id: str, notes: Optional[str] = None, db: Session = Depends(get_db), current_user: Employee = Depends(require_store_manager)):
    assignment = db.query(StaffAssignment).filter(StaffAssignment.id == assignment_id).first()
    if not assignment:
        raise HTTPException(status_code=404, detail="Assignment not found")

    new_shelf = db.query(Shelf).filter(and_(Shelf.name == new_shelf_id, Shelf.is_active == True)).first()
    if not new_shelf:
        raise HTTPException(status_code=404, detail="New shelf not found or inactive")

    old_shelf_id = assignment.shelf_id
    assignment.shelf_id = new_shelf_id
    assignment.notes = notes
    db.commit()
    db.refresh(assignment)

    history = AssignmentHistory(
        employee_id=assignment.employee_id,
        shelf_id=new_shelf_id,
        action="transferred",
        performed_by=current_user.employee_id,
        notes=f"Transferred from shelf {old_shelf_id} to {new_shelf_id}. {notes or ''}"
    )
    db.add(history)
    db.commit()

    manager = db.query(Employee).filter(Employee.employee_id == assignment.assigned_by).first()

    return StaffAssignmentResponse(
        id=assignment.id,
        employee_id=assignment.employee_id,
        employee_name=assignment.employee.username,
        shelf_id=assignment.shelf.name,
        shelf_name=assignment.shelf.name,
        shelf_category=assignment.shelf.category.value if hasattr(assignment.shelf.category, 'value') else str(assignment.shelf.category),
        is_active=assignment.is_active,
        assigned_at=assignment.assigned_at,
        assigned_date=assignment.assigned_at,  # ✅ Fix 1
        created_at=assignment.created_at,      # ✅ Fix 2
        updated_at=assignment.updated_at,      # ✅ Fix 3
        assigned_by=assignment.assigned_by,
        assigned_by_name=manager.username if manager else "Unknown",
        notes=assignment.notes
    )
