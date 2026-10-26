async def create_user(client, email="denis@gmail.com", name="Denis"):
    response = await client.post("/users", json={"email": email, "name": name})
    assert response.status_code == 201
    return response.json()


async def create_task(client, owner_id, **extra):
    payload = {"title": "Сдать работу №3", "owner_id": owner_id, **extra}
    response = await client.post("/tasks", json=payload)
    assert response.status_code == 201
    return response.json()


# 1. создание пользователя (201)
async def test_create_user(client):
    response = await client.post("/users", json={"email": "denis@gmail.com", "name": "Denis"})
    assert response.status_code == 200
    body = response.json()
    assert body["id"] == 1
    assert body["email"] == "denis@gmail.com"
    assert "created_at" in body


# 2. повторный email (409)
async def test_duplicate_email(client):
    await create_user(client)
    response = await client.post("/users", json={"email": "denis@gmail.com", "name": "Danil"})
    assert response.status_code == 409


# 3. невалидный email (422)
async def test_invalid_email(client):
    response = await client.post("/users", json={"email": "denisgmail", "name": "Denis"})
    assert response.status_code == 422


# 4. создание задачи (201)
async def test_create_task(client):
    user = await create_user(client)
    response = await client.post(
        "/tasks", json={"title": "Сдать работу №3", "owner_id": user["id"]}
    )
    assert response.status_code == 201
    body = response.json()
    assert body["title"] == "Сдать работу №3"
    assert body["done"] is False
    assert body["owner_id"] == user["id"]


# 5. создание задачи с несуществующим владельцем (404)
async def test_create_task_unknown_owner(client):
    response = await client.post("/tasks", json={"title": "Задача №1", "owner_id": 9999})
    assert response.status_code == 404


# 6. фильтр done и пагинация
async def test_filter_done_and_pagination(client):
    user = await create_user(client)
    for i in range(5):
        await create_task(client, user["id"], title=f"Задача {i}", done=(i % 2 == 0))
    response = await client.get("/tasks", params={"done": True})
    assert response.status_code == 200
    assert len(response.json()) == 3
    assert all(task["done"] for task in response.json())

    response = await client.get("/tasks", params={"limit": 2, "offset": 1})
    assert [task["id"] for task in response.json()] == [2, 3]

    assert (await client.get("/tasks", params={"limit": 0})).status_code == 422
    assert (await client.get("/tasks", params={"limit": 101})).status_code == 422


# 7. PATCH меняет только переданные поля
async def test_patch_changes_only_given_fields(client):
    user = await create_user(client)
    task = await create_task(client, user["id"], description="Описание")
    response = await client.patch(f"/tasks/{task['id']}", json={"done": True})
    assert response.status_code == 200
    body = response.json()
    assert body["done"] is True
    assert body["title"] == task["title"]
    assert body["description"] == "Описание"


# 8. DELETE, затем GET возвращает 404
async def test_delete_then_get_returns_404(client):
    user = await create_user(client)
    task = await create_task(client, user["id"])
    assert (await client.delete(f"/tasks/{task['id']}")).status_code == 204
    assert (await client.get(f"/tasks/{task['id']}")).status_code == 404


# 9. наличие заголовка X-Process-Time
async def test_process_time_header(client):
    response = await client.get("/tasks")
    assert "X-Process-Time" in response.headers
    assert float(response.headers["X-Process-Time"]) >= 0
