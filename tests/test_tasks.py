def test_create_and_get(client):
    r = client.post("/api/v1/tasks", json={"title": "  write pipeline  "})
    assert r.status_code == 201
    task = r.get_json()
    assert task["title"] == "write pipeline"
    assert task["done"] is False

    r = client.get(f"/api/v1/tasks/{task['id']}")
    assert r.status_code == 200


def test_list(client):
    client.post("/api/v1/tasks", json={"title": "a"})
    client.post("/api/v1/tasks", json={"title": "b"})
    assert len(client.get("/api/v1/tasks").get_json()) == 2


def test_update(client):
    tid = client.post("/api/v1/tasks", json={"title": "a"}).get_json()["id"]
    r = client.patch(f"/api/v1/tasks/{tid}", json={"done": True, "title": "renamed"})
    assert r.status_code == 200
    assert r.get_json()["done"] is True
    assert r.get_json()["title"] == "renamed"


def test_delete(client):
    tid = client.post("/api/v1/tasks", json={"title": "a"}).get_json()["id"]
    assert client.delete(f"/api/v1/tasks/{tid}").status_code == 204
    assert client.get(f"/api/v1/tasks/{tid}").status_code == 404


def test_validation(client):
    assert client.post("/api/v1/tasks", json={}).status_code == 400
    assert client.post("/api/v1/tasks", json={"title": ""}).status_code == 400
    assert client.post("/api/v1/tasks", json={"title": 123}).status_code == 400
    assert client.post("/api/v1/tasks", json={"title": "x" * 121}).status_code == 400
    tid = client.post("/api/v1/tasks", json={"title": "a"}).get_json()["id"]
    assert client.patch(f"/api/v1/tasks/{tid}", json={"done": "yes"}).status_code == 400


def test_not_found_is_json(client):
    r = client.get("/api/v1/tasks/999")
    assert r.status_code == 404
    assert r.get_json() == {"error": "Not Found"}


def test_sql_injection_attempt_is_stored_as_plain_text(client):
    payload = "'; DROP TABLE tasks;--"
    assert client.post("/api/v1/tasks", json={"title": payload}).status_code == 201
    assert client.get("/api/v1/tasks").get_json()[0]["title"] == payload
