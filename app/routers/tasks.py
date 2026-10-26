from fastapi import APIRouter, Depends, HTTPException, Query, status

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_session
from app.models import Task, User
from app.schemas import TaskCreate, TaskRead, TaskUpdate


router = APIRouter(prefix="/tasks", tags=["tasks"])

@router.post("", response_model=TaskRead, status_code=status.HTTP_201_CREATED)
async def create_task(data: TaskCreate, session: AsyncSession = Depends(get_session)):
    owner = await session.get(User, data.owner_id)
    if owner is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Owner not found")

    task = Task(**data.model_dump())
    session.add(task)
    await session.commit()
    await session.refresh(task)
    return task

@router.get("", response_model=list[TaskRead])
async def list_tasks(
    done: bool | None = None,
    owner_id: int | None = None,
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    session: AsyncSession = Depends(get_session),
):
    stmt = select(Task).order_by(Task.id)
    if done is not None:
        stmt = stmt.where(Task.done == done)
    if owner_id is not None:
        stmt = stmt.where(Task.owner_id == owner_id)
    stmt = stmt.limit(limit).offset(offset)

    result = await session.scalars(stmt)
    return result.all()

@router.get("/{task_id}", response_model=TaskRead)
async def get_task(task_id: int, session: AsyncSession = Depends(get_session)):
    task = await session.get(Task, task_id)
    if task is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Task not found")
    return task

@router.patch("/{task_id}", response_model=TaskRead)
async def update_task(
    task_id: int, data: TaskUpdate, session: AsyncSession = Depends(get_session)
):
    task = await session.get(Task, task_id)
    if task is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Task not found")

    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(task, field, value)

    await session.commit()
    await session.refresh(task)
    return task

@router.delete("/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_task(task_id: int, session: AsyncSession = Depends(get_session)):
    task = await session.get(Task, task_id)
    if task is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Task not found")
    await session.delete(task)
    await session.commit()
