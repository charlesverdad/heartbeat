"""Unit tests for multi-role RBAC system."""

import pytest
from uuid import uuid4
from app.models import User, Role, UserRole, Permission, Folder, Page


@pytest.mark.asyncio
async def test_create_custom_role(async_client, admin_token):
    """Test creating a custom role."""
    response = await async_client.post(
        "/roles/",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={
            "name": "Content Team",
            "description": "Manages content creation and editing"
        }
    )
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == "content-team"
    assert data["name"] == "Content Team"
    assert data["is_system"] is False
    assert data["user_count"] == 0


@pytest.mark.asyncio
async def test_list_roles(async_client, admin_token):
    """Test listing all roles."""
    response = await async_client.get(
        "/roles/",
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert response.status_code == 200
    roles = response.json()
    assert len(roles) >= 4  # At least the 4 system roles
    
    # Check system roles exist
    role_ids = [r["id"] for r in roles]
    assert "superadmin" in role_ids
    assert "admin" in role_ids
    assert "member" in role_ids
    assert "public" in role_ids


@pytest.mark.asyncio
async def test_update_custom_role(async_client, admin_token, db_session):
    """Test updating a custom role."""
    # Create a custom role first
    role = Role(
        id="test-role",
        name="Test Role",
        is_system=False,
        description="Original description"
    )
    db_session.add(role)
    await db_session.commit()
    
    # Update it
    response = await async_client.patch(
        "/roles/test-role",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={
            "name": "Updated Test Role",
            "description": "Updated description"
        }
    )
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Updated Test Role"
    assert data["description"] == "Updated description"


@pytest.mark.asyncio
async def test_cannot_update_system_role(async_client, admin_token):
    """Test that system roles cannot be updated."""
    response = await async_client.patch(
        "/roles/superadmin",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={"name": "Hacked Admin"}
    )
    assert response.status_code == 400
    assert "system roles" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_delete_custom_role(async_client, admin_token, db_session):
    """Test deleting a custom role with no users."""
    # Create a custom role
    role = Role(
        id="deletable-role",
        name="Deletable Role",
        is_system=False
    )
    db_session.add(role)
    await db_session.commit()
    
    # Delete it
    response = await async_client.delete(
        "/roles/deletable-role",
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert response.status_code == 204


@pytest.mark.asyncio
async def test_cannot_delete_role_with_users(async_client, admin_token, db_session, test_user):
    """Test that roles with assigned users cannot be deleted."""
    # Create a custom role
    role = Role(
        id="assigned-role",
        name="Assigned Role",
        is_system=False
    )
    db_session.add(role)
    await db_session.flush()
    
    # Assign it to a user
    user_role = UserRole(user_id=test_user.id, role_id="assigned-role")
    db_session.add(user_role)
    await db_session.commit()
    
    # Try to delete it
    response = await async_client.delete(
        "/roles/assigned-role",
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert response.status_code == 400
    assert "assigned users" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_assign_multiple_roles_to_user(async_client, admin_token, test_user):
    """Test assigning multiple roles to a user."""
    response = await async_client.post(
        f"/roles/users/{test_user.id}/roles",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={"role_ids": ["member", "admin"]}
    )
    assert response.status_code == 204
    
    # Verify roles were assigned
    response = await async_client.get(
        f"/roles/users/{test_user.id}/roles",
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert response.status_code == 200
    role_ids = response.json()
    assert "member" in role_ids
    assert "admin" in role_ids


@pytest.mark.asyncio
async def test_multi_role_permission_check(db_session, test_user):
    """Test that permission checking works across multiple roles."""
    from app.services import check_permission
    
    # Create a test folder
    folder = Folder(id=uuid4(), name="Test Folder")
    db_session.add(folder)
    await db_session.flush()
    
    # Assign user two roles
    user_role1 = UserRole(user_id=test_user.id, role_id="member")
    user_role2 = UserRole(user_id=test_user.id, role_id="admin")
    db_session.add(user_role1)
    db_session.add(user_role2)
    await db_session.flush()
    
    # Grant VIEW permission to member role
    perm = Permission(
        subject_type="ROLE",
        subject_id="member",
        object_type="FOLDER",
        object_id=folder.id,
        level="VIEW"
    )
    db_session.add(perm)
    await db_session.commit()
    
    # Refresh user to load relationships
    await db_session.refresh(test_user, ["user_roles"])
    
    # User should have VIEW access through member role
    has_access = await check_permission(db_session, test_user, folder.id, "FOLDER", "VIEW")
    assert has_access is True


@pytest.mark.asyncio
async def test_superadmin_role_has_all_permissions(db_session, admin_user):
    """Test that superadmin role grants access to everything."""
    from app.services import check_permission
    
    # Create a private folder with no permissions
    folder = Folder(id=uuid4(), name="Private Folder", is_public=False)
    db_session.add(folder)
    await db_session.commit()
    
    # Refresh admin user to load relationships
    await db_session.refresh(admin_user, ["user_roles"])
    
    # Superadmin should have MANAGE access even without explicit permission
    has_access = await check_permission(db_session, admin_user, folder.id, "FOLDER", "MANAGE")
    assert has_access is True


@pytest.mark.asyncio
async def test_user_with_no_roles_only_sees_public(db_session):
    """Test that users with no roles can only access public content."""
    from app.services import check_permission
    
    # Create user with no roles
    user = User(
        email="norole@test.com",
        full_name="No Role User"
    )
    db_session.add(user)
    await db_session.flush()
    
    # Create public and private folders
    public_folder = Folder(id=uuid4(), name="Public Folder", is_public=True)
    private_folder = Folder(id=uuid4(), name="Private Folder", is_public=False)
    db_session.add(public_folder)
    db_session.add(private_folder)
    await db_session.commit()
    
    # Refresh user
    await db_session.refresh(user, ["user_roles"])
    
    # Should have VIEW access to public folder
    has_public_access = await check_permission(db_session, user, public_folder.id, "FOLDER", "VIEW")
    assert has_public_access is True
    
    # Should NOT have access to private folder
    has_private_access = await check_permission(db_session, user, private_folder.id, "FOLDER", "VIEW")
    assert has_private_access is False


@pytest.mark.asyncio
async def test_remove_role_from_user(async_client, admin_token, test_user, db_session):
    """Test removing a role from a user."""
    # Assign two roles
    user_role1 = UserRole(user_id=test_user.id, role_id="member")
    user_role2 = UserRole(user_id=test_user.id, role_id="admin")
    db_session.add(user_role1)
    db_session.add(user_role2)
    await db_session.commit()
    
    # Remove one role
    response = await async_client.delete(
        f"/roles/users/{test_user.id}/roles/member",
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert response.status_code == 204
    
    # Verify only admin role remains
    response = await async_client.get(
        f"/roles/users/{test_user.id}/roles",
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    role_ids = response.json()
    assert "admin" in role_ids
    assert "member" not in role_ids



@pytest.mark.asyncio
async def test_update_user_roles_via_admin(async_client, admin_token, test_user):
    """Test updating user roles via admin endpoint."""
    response = await async_client.patch(
        f"/admin/users/{test_user.id}",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={
            "full_name": "Updated Name",
            "role_ids": ["admin", "member"]
        }
    )
    assert response.status_code == 200
    data = response.json()
    assert data["full_name"] == "Updated Name"
    assert "admin" in data["roles"]
    assert "member" in data["roles"]

