from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.rag_engine import collection_exists
from app.db.crud import get_all_roles
from app.db.database import get_db
from app.db.schemas import RoleOut

router = APIRouter(prefix="/api/roles", tags=["roles"])


@router.get("", response_model=list[RoleOut])
def list_roles(db: Session = Depends(get_db)):
    roles = get_all_roles(db)
    result = []
    for role in roles:
        result.append(
            RoleOut(
                id=role.id,
                name=role.name,
                description=role.description,
                kb_ready=collection_exists(role.kb_collection_name),
            )
        )
    return result
