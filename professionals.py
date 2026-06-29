from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List
import uuid

from app.database import get_db
from app.dependencies import require_operator_or_admin, get_current_user
from app.models import AvailabilityRule
from app.schemas import AvailabilityRuleCreate, AvailabilityRuleResponse

router = APIRouter(prefix="/availability", tags=["Disponibilidade"])

@router.get("", response_model=List[AvailabilityRuleResponse])
async def list_rules(professional_id: uuid.UUID = None, db: AsyncSession = Depends(get_db)):
    query = select(AvailabilityRule)
    if professional_id:
        query = query.where(AvailabilityRule.professional_id == professional_id)
    
    result = await db.execute(query)
    return result.scalars().all()

@router.post("", response_model=AvailabilityRuleResponse, status_code=status.HTTP_201_CREATED)
async def create_rule(
    rule: AvailabilityRuleCreate,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user)
):
    if current_user.role != "master":
        raise HTTPException(status_code=403, detail="Apenas admin pode gerenciar horários")
    
    new_rule = AvailabilityRule(**rule.model_dump())
    db.add(new_rule)
    await db.commit()
    await db.refresh(new_rule)
    return new_rule

@router.delete("/{rule_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_availability_rule(
    rule_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user)
):
    if current_user.role != "master":
        raise HTTPException(status_code=403, detail="Apenas admin pode gerenciar horários")
        
    rule = await db.get(AvailabilityRule, rule_id)
    if not rule:
        raise HTTPException(status_code=404, detail="Regra não encontrada")
        
    await db.delete(rule)
    await db.commit()
