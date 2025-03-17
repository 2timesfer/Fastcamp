from datetime import datetime
from typing import Optional
from uuid import uuid4

from fastapi import FastAPI
from fastapi.responses import JSONResponse
from fastapi.testclient import TestClient
from pydantic import BaseModel, EmailStr, Field, field_serializer, UUID4

app = FastAPI()

class User(BaseModel):
    model_config = {
        'extra': 'forbid',
    }
    __users__ = []
    __tasks__ = [] #lista de tarefas do usuario
    
    name: str = Field(..., description='Nome do usuário')
    email: EmailStr = Field(..., description='Email do usuário')
    tasks: list[UUID4] = Field(default_factory=list, description="IDs das tarefas do usuário")
    friends: list[UUID4] = Field(
        default_factory=list, max_items=500, description='Lista de amigos'
    )
    blocked: list[UUID4] = Field(
        default_factory=list, max_items=500, description='Lista de usuários bloqueados'
    )
    signup_ts: Optional[datetime] = Field(
        default_factory=datetime.now, description= 'Horário de cadastro', kw_only=True
    )
    id: UUID4 = Field(
        default_factory=uuid4, description='Identificador único', kw_only=True
    )

    @field_serializer('id', when_used='json')
    def serialize_id(self, id: UUID4) -> str:
        return str(id)

    def add_task(self, task_id: UUID4):
        if not hasattr(self, "tasks"):
            self.tasks = []
        self.tasks.append(task_id)
        
class Task(BaseModel):
    model_config = {
        'extra': 'forbid',
    }
    __tasks__ = []
    
    user_id : UUID4
    title: str = Field(..., min_length=3, description= 'Título da tarefa')
    task_desc: Optional[str] = None
    completed: bool = Field(default=False, description= 'Estado de completude da tarefa')
    created_at: datetime = Field(default_factory=datetime.now, description= 'Horário de cadastro', kw_only=True)
    id: UUID4 = Field(
        default_factory=uuid4, description='Identificador único', kw_only=True
    )
    @field_serializer('id', when_used='json')
    def serialize_id(self, id: UUID4) -> str:
        return str(id)
    
@app.get('/users', response_model=list[User])
async def get_users() -> list[User]:
    return list(User.__users__)

@app.post('/users', response_model=User)
async def create_user(user: User):
    User.__users__.append(user)
    return user

@app.get('/users/{user_id}', response_model=User)
async def get_user(user_id: UUID4) -> User | JSONResponse:
    try:
        return next((user for user in User.__users__ if user.id == user_id))
    except StopIteration:
        return JSONResponse(status_code=404, content={'message': 'Usuário não encontrado'})
    
@app.post('/tasks', response_model=Task)
async def create_task(task: Task):
    try:
        user = next((user for user in User.__users__ if user.id == task.user_id), None)
        User.__tasks__.append(task)
        user.tasks.append(task.id)
        return task
    except:
        return JSONResponse(status_code=404, content={'message': 'Task só pode ser associada a um usuário cadastrado.'})
    

@app.get('/users/{user_id}/tasks', response_model=list[Task])
async def get_user_tasks(user_id: UUID4):
    user_tasks = [task for task in User.__tasks__ if task.user_id == user_id]
    return user_tasks

@app.get("/tasks/{task_id}", response_model=Task)
async def get_task(task_id: UUID4):
    try:
        task = next((task for task in User.__tasks__ if task.id == task_id), None)
        return task
    except:
        return JSONResponse(status_code=404, content={'message': 'Tarefa não encontrada.'})

@app.put("/tasks/{task_id}", response_model=Task)
async def update_task(task_id: UUID4):
    try:
        task = next((task for task in User.__tasks__ if task.id == task_id), None)
        task.completed = True
        return task
    except:
        return JSONResponse(status_code=404, content={'message': 'Tarefa não encontrada.'})
    

@app.delete("/tasks/{task_id}")
async def delete_task(task_id: UUID4):
    task = next((task for task in User.__tasks__ if task.id == task_id), None)
    if not task:
        return JSONResponse(status_code=404, content={'message': 'Tarefa não encontrada.'})
    
    User.__tasks__.remove(task)

    # Remover da lista de tarefas do usuário
    user = next((user for user in User.__users__ if user.id == task.user_id), None)
    if user:
        user.tasks.remove(task.id)

    return {"message": "Tarefa removida com sucesso"}

def main() -> None:
     with TestClient(app) as client:
        # Criando um usuário
        response = client.post("/users", json={"name": "User", "email": "user@dominio.com"})
        assert response.status_code == 200
        user_id = response.json()["id"]

        # Criando uma tarefa para o usuário
        response = client.post("/tasks", json={"user_id": user_id, "title": "Estudar Python"})
        assert response.status_code == 200
        task_id = response.json()["id"]

        # Verificando se a tarefa aparece na lista do usuário
        response = client.get(f"/users/{user_id}/tasks")
        assert response.status_code == 200
        assert len(response.json()) == 1
        assert response.json()[0]["title"] == "Estudar Python"

        # Atualizando a tarefa (marcando como concluída)
        response = client.put(f"/tasks/{task_id}")
        assert response.status_code == 200
        assert response.json()["completed"] == True

        # Deletando a tarefa
        response = client.delete(f"/tasks/{task_id}")
        assert response.status_code == 200

        # Verificando se a tarefa foi removida corretamente
        response = client.get(f"/tasks/{task_id}")
        assert response.status_code == 404

if __name__ == '__main__':
    main()