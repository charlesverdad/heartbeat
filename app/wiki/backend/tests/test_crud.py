import pytest
from uuid import uuid4

@pytest.mark.asyncio
async def test_create_folder(async_client, admin_token):
    response = await async_client.post(
        "/folders",
        json={"name": "Test Folder"},
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Test Folder"
    assert "id" in data

@pytest.mark.asyncio
async def test_create_page(async_client, admin_token):
    # First create a folder
    f_res = await async_client.post(
        "/folders",
        json={"name": "Parent Folder"},
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert f_res.status_code == 200
    folder_id = f_res.json()["id"]

    # Create a page in that folder
    response = await async_client.post(
        "/pages/",
        json={
            "title": "Test Page",
            "content": "Test Content",
            "folder_id": folder_id
        },
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["title"] == "Test Page"
    assert data["folder_id"] == folder_id

@pytest.mark.asyncio
async def test_public_access(async_client, admin_token):
    # Create a public page
    p_res = await async_client.post(
        "/pages/",
        json={
            "title": "Public Page",
            "content": "Public Content",
            "is_public": True
        },
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert p_res.status_code == 200
    page_id = p_res.json()["id"]

    # Access without token
    response = await async_client.get(f"/pages/{page_id}")
    assert response.status_code == 200
    assert response.json()["title"] == "Public Page"

@pytest.mark.asyncio
async def test_private_access_denied(async_client, admin_token):
    # Create a private page
    p_res = await async_client.post(
        "/pages/",
        json={
            "title": "Private Page",
            "content": "Private Content",
            "is_public": False
        },
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert p_res.status_code == 200
    page_id = p_res.json()["id"]

    # Access without token
    response = await async_client.get(f"/pages/{page_id}")
    assert response.status_code == 404 # Our API returns 404 for access denied
