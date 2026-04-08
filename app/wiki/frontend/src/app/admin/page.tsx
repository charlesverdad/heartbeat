"use client";

import { useState, useEffect, useCallback, useMemo, useRef } from "react";
import { useRouter } from "next/navigation";
import Fuse from "fuse.js";
import styles from "./admin.module.css";

interface UserDetail {
    id: string;
    email: string;
    full_name: string;
    roles: string[];
}

interface RoleDetail {
    id: string;
    name: string;
    is_system: boolean;
    description: string | null;
    user_count: number;
    created_at: string;
}

export default function AdminPanel() {
    const [users, setUsers] = useState<UserDetail[]>([]);
    const [roles, setRoles] = useState<RoleDetail[]>([]);
    const [pages, setPages] = useState<any[]>([]);
    const [settings, setSettings] = useState<any[]>([]);
    const [activeTab, setActiveTab] = useState("users");
    const [loading, setLoading] = useState(true);
    const [editingUser, setEditingUser] = useState<UserDetail | null>(null);
    const [creatingRole, setCreatingRole] = useState(false);
    const [newRole, setNewRole] = useState({ name: "", description: "" });
    const [editingRole, setEditingRole] = useState<RoleDetail | null>(null);
    const [savedSettings, setSavedSettings] = useState<Set<string>>(new Set());
    const [homePageSearch, setHomePageSearch] = useState("");
    const [isHomePageDropdownOpen, setIsHomePageDropdownOpen] = useState(false);
    const dropdownRef = useRef<HTMLDivElement>(null);
    const router = useRouter();

    const fetchAdminData = useCallback(async (token: string) => {
        try {
            const [usersRes, rolesRes, pagesRes, settingsRes] = await Promise.all([
                fetch("http://localhost:8000/admin/users", {
                    headers: { "Authorization": `Bearer ${token}` }
                }),
                fetch("http://localhost:8000/roles", {
                    headers: { "Authorization": `Bearer ${token}` }
                }),
                fetch("http://localhost:8000/pages", {
                    headers: { "Authorization": `Bearer ${token}` }
                }),
                fetch("http://localhost:8000/settings")
            ]);

            if (usersRes.status === 403) {
                alert("Only Super Admins can access this panel");
                router.push("/");
                return;
            }

            if (usersRes.ok && rolesRes.ok && pagesRes.ok && settingsRes.ok) {
                setUsers(await usersRes.json());
                setRoles(await rolesRes.json());
                setPages(await pagesRes.json());
                setSettings(await settingsRes.json());
            }
        } catch (error) {
            console.error("Fetch error:", error);
        } finally {
            setLoading(false);
        }
    }, [router]);

    useEffect(() => {
        const token = localStorage.getItem("wiki_token");
        if (!token) {
            router.push("/login");
            return;
        }
        fetchAdminData(token);
    }, [router, fetchAdminData]);

    const handleUpdateUser = async (userId: string, updatedData: any) => {
        const token = localStorage.getItem("wiki_token");
        try {
            const res = await fetch(`http://localhost:8000/admin/users/${userId}`, {
                method: "PATCH",
                headers: {
                    "Content-Type": "application/json",
                    "Authorization": `Bearer ${token}`
                },
                body: JSON.stringify(updatedData)
            });
            if (res.ok) {
                setEditingUser(null);
                fetchAdminData(token!);
            }
        } catch (error) {
            console.error("Update error:", error);
        }
    };

    const handleCreateRole = async () => {
        const token = localStorage.getItem("wiki_token");
        try {
            const res = await fetch("http://localhost:8000/roles/", {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                    "Authorization": `Bearer ${token}`
                },
                body: JSON.stringify(newRole)
            });
            if (res.ok) {
                setCreatingRole(false);
                setNewRole({ name: "", description: "" });
                fetchAdminData(token!);
            }
        } catch (error) {
            console.error("Create role error:", error);
        }
    };

    const handleUpdateRole = async (roleId: string, updatedData: { name?: string; description?: string }) => {
        const token = localStorage.getItem("wiki_token");
        try {
            const res = await fetch(`http://localhost:8000/roles/${roleId}`, {
                method: "PATCH",
                headers: {
                    "Content-Type": "application/json",
                    "Authorization": `Bearer ${token}`
                },
                body: JSON.stringify(updatedData)
            });
            if (res.ok) {
                setEditingRole(null);
                fetchAdminData(token!);
            }
        } catch (error) {
            console.error("Update role error:", error);
        }
    };

    const handleDeleteRole = async (roleId: string) => {
        if (!confirm("Are you sure you want to delete this role?")) return;

        const token = localStorage.getItem("wiki_token");
        try {
            const res = await fetch(`http://localhost:8000/roles/${roleId}`, {
                method: "DELETE",
                headers: { "Authorization": `Bearer ${token}` }
            });
            if (res.ok) {
                fetchAdminData(token!);
            } else {
                const error = await res.json();
                alert(error.detail || "Failed to delete role");
            }
        } catch (error) {
            console.error("Delete role error:", error);
        }
    };

    const handleUpdateSetting = async (key: string, value: string) => {
        const token = localStorage.getItem("wiki_token");
        try {
            const res = await fetch(`http://localhost:8000/settings/${key}`, {
                method: "PUT",
                headers: {
                    "Content-Type": "application/json",
                    "Authorization": `Bearer ${token}`
                },
                body: JSON.stringify({ value })
            });
            if (res.ok) {
                setSavedSettings(prev => new Set(prev).add(key));
                setTimeout(() => {
                    setSavedSettings(prev => {
                        const newSet = new Set(prev);
                        newSet.delete(key);
                        return newSet;
                    });
                }, 2000);
            }
        } catch (error) {
            console.error("Update setting error:", error);
        }
    };

    const toggleUserRole = (roleId: string) => {
        if (!editingUser) return;
        const roles = editingUser.roles.includes(roleId)
            ? editingUser.roles.filter(r => r !== roleId)
            : [...editingUser.roles, roleId];
        setEditingUser({ ...editingUser, roles });
    };

    // Fuse.js search for home page
    const fuse = useMemo(() => {
        return new Fuse(pages, {
            keys: ["title"],
            threshold: 0.3
        });
    }, [pages]);

    const filteredPages = useMemo(() => {
        if (!homePageSearch) return pages;
        return fuse.search(homePageSearch).map(result => result.item);
    }, [homePageSearch, fuse, pages]);

    useEffect(() => {
        const handleClickOutside = (event: MouseEvent) => {
            if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
                setIsHomePageDropdownOpen(false);
            }
        };
        document.addEventListener("mousedown", handleClickOutside);
        return () => document.removeEventListener("mousedown", handleClickOutside);
    }, []);

    if (loading) {
        return <div className={styles.loading}>Loading admin panel...</div>;
    }

    return (
        <div className={styles.adminPanel}>
            <h1>Admin Panel</h1>

            <div className={styles.tabs}>
                <button
                    className={activeTab === "users" ? styles.activeTab : ""}
                    onClick={() => setActiveTab("users")}
                >
                    Users
                </button>
                <button
                    className={activeTab === "roles" ? styles.activeTab : ""}
                    onClick={() => setActiveTab("roles")}
                >
                    Roles & Groups
                </button>
                <button
                    className={activeTab === "settings" ? styles.activeTab : ""}
                    onClick={() => setActiveTab("settings")}
                >
                    System Settings
                </button>
            </div>

            <div className={styles.tabContent}>
                {activeTab === "users" && (
                    <div className={styles.userList}>
                        <div className={styles.tableHeader}>
                            <span>Email</span>
                            <span>Full Name</span>
                            <span>Roles</span>
                            <span>Actions</span>
                        </div>
                        {users.map(user => (
                            <div key={user.id} className={styles.tableRow}>
                                <span>{user.email}</span>
                                <div className={styles.nameColumn}>
                                    {editingUser?.id === user.id ? (
                                        <input
                                            value={editingUser.full_name || ""}
                                            onChange={(e) => setEditingUser({ ...editingUser, full_name: e.target.value })}
                                            className={styles.nameInput}
                                        />
                                    ) : (
                                        <span>{user.full_name}</span>
                                    )}
                                </div>
                                <div className={styles.roleColumn}>
                                    {editingUser?.id === user.id ? (
                                        <div className={styles.roleCheckboxes}>
                                            {roles.map(r => (
                                                <label key={r.id} className={styles.roleCheckbox}>
                                                    <input
                                                        type="checkbox"
                                                        checked={editingUser.roles.includes(r.id)}
                                                        onChange={() => toggleUserRole(r.id)}
                                                    />
                                                    <span>{r.name}</span>
                                                </label>
                                            ))}
                                        </div>
                                    ) : (
                                        <div className={styles.roleBadges}>
                                            {user.roles.map(roleId => {
                                                const role = roles.find(r => r.id === roleId);
                                                return (
                                                    <span key={roleId} className={styles.roleBadge}>
                                                        {role?.name || roleId}
                                                    </span>
                                                );
                                            })}
                                        </div>
                                    )}
                                </div>
                                <div className={styles.actions}>
                                    {editingUser?.id === user.id ? (
                                        <>
                                            <button onClick={() => handleUpdateUser(user.id, {
                                                full_name: editingUser.full_name,
                                                role_ids: editingUser.roles
                                            })}>
                                                Save
                                            </button>
                                            <button onClick={() => setEditingUser(null)}>Cancel</button>
                                        </>
                                    ) : (
                                        <button onClick={() => setEditingUser(user)}>Edit</button>
                                    )}
                                </div>
                            </div>
                        ))}
                    </div>
                )}

                {activeTab === "roles" && (
                    <div className={styles.roleList}>
                        <div className={styles.roleHeader}>
                            <h2>Roles & Groups</h2>
                            <button
                                className={styles.createButton}
                                onClick={() => setCreatingRole(true)}
                            >
                                + Create Role
                            </button>
                        </div>

                        {creatingRole && (
                            <div className={styles.roleForm}>
                                <h3>Create New Role</h3>
                                <div className={styles.formGroup}>
                                    <label>Role Name</label>
                                    <input
                                        value={newRole.name}
                                        onChange={(e) => setNewRole({ ...newRole, name: e.target.value })}
                                        placeholder="e.g., Media Team"
                                    />
                                </div>
                                <div className={styles.formGroup}>
                                    <label>Description</label>
                                    <textarea
                                        value={newRole.description}
                                        onChange={(e) => setNewRole({ ...newRole, description: e.target.value })}
                                        placeholder="Optional description"
                                    />
                                </div>
                                <div className={styles.formActions}>
                                    <button onClick={handleCreateRole}>Create</button>
                                    <button onClick={() => {
                                        setCreatingRole(false);
                                        setNewRole({ name: "", description: "" });
                                    }}>Cancel</button>
                                </div>
                            </div>
                        )}

                        <div className={styles.rolesGrid}>
                            <h3>System Roles</h3>
                            {roles.filter(r => r.is_system).map(role => (
                                <div key={role.id} className={styles.roleCard}>
                                    <div className={styles.roleCardHeader}>
                                        <h4>{role.name}</h4>
                                        <span className={styles.systemBadge}>System</span>
                                    </div>
                                    <p className={styles.roleDescription}>{role.description}</p>
                                    <div className={styles.roleStats}>
                                        <span>{role.user_count} members</span>
                                    </div>
                                </div>
                            ))}

                            <h3 style={{ marginTop: "2rem" }}>Custom Roles</h3>
                            {roles.filter(r => !r.is_system).length === 0 ? (
                                <p className={styles.emptyState}>No custom roles yet. Create one to get started!</p>
                            ) : (
                                roles.filter(r => !r.is_system).map(role => (
                                    <div key={role.id} className={styles.roleCard}>
                                        {editingRole?.id === role.id ? (
                                            <div className={styles.roleEditForm}>
                                                <input
                                                    value={editingRole.name}
                                                    onChange={(e) => setEditingRole({ ...editingRole, name: e.target.value })}
                                                    className={styles.roleNameInput}
                                                />
                                                <textarea
                                                    value={editingRole.description || ""}
                                                    onChange={(e) => setEditingRole({ ...editingRole, description: e.target.value })}
                                                    className={styles.roleDescInput}
                                                />
                                                <div className={styles.roleEditActions}>
                                                    <button onClick={() => handleUpdateRole(role.id, {
                                                        name: editingRole.name,
                                                        description: editingRole.description || undefined
                                                    })}>Save</button>
                                                    <button onClick={() => setEditingRole(null)}>Cancel</button>
                                                </div>
                                            </div>
                                        ) : (
                                            <>
                                                <div className={styles.roleCardHeader}>
                                                    <h4>{role.name}</h4>
                                                    <div className={styles.roleActions}>
                                                        <button onClick={() => setEditingRole(role)}>Edit</button>
                                                        <button
                                                            onClick={() => handleDeleteRole(role.id)}
                                                            className={styles.deleteButton}
                                                        >
                                                            Delete
                                                        </button>
                                                    </div>
                                                </div>
                                                <p className={styles.roleDescription}>{role.description || "No description"}</p>
                                                <div className={styles.roleStats}>
                                                    <span>{role.user_count} members</span>
                                                </div>
                                            </>
                                        )}
                                    </div>
                                ))
                            )}
                        </div>
                    </div>
                )}

                {activeTab === "settings" && (
                    <div className={styles.settingsPanel}>
                        <div className={styles.settingItem}>
                            <h3>Site Identity</h3>
                            <div className={styles.inputGroup}>
                                <label>Site Name</label>
                                <input
                                    value={settings.find(s => s.key === "site_name")?.value || ""}
                                    onChange={(e) => handleUpdateSetting("site_name", e.target.value)}
                                    placeholder="Wiki"
                                    className={savedSettings.has("site_name") ? styles.saved : ""}
                                />
                            </div>
                        </div>
                        <div className={styles.settingItem}>
                            <h3>Navigation</h3>
                            <div className={styles.inputGroup}>
                                <label>Home Page</label>
                                <div className={styles.searchableWrapper} ref={dropdownRef}>
                                    <input
                                        value={homePageSearch}
                                        onChange={(e) => {
                                            setHomePageSearch(e.target.value);
                                            setIsHomePageDropdownOpen(true);
                                        }}
                                        onFocus={() => setIsHomePageDropdownOpen(true)}
                                        placeholder="Search for a page..."
                                        className={savedSettings.has("home_page_id") ? styles.saved : ""}
                                    />
                                    {isHomePageDropdownOpen && (
                                        <div className={styles.searchDropdown}>
                                            {filteredPages.slice(0, 10).map(page => (
                                                <div
                                                    key={page.id}
                                                    className={styles.searchResult}
                                                    onClick={() => {
                                                        handleUpdateSetting("home_page_id", page.id);
                                                        setHomePageSearch(page.title);
                                                        setIsHomePageDropdownOpen(false);
                                                    }}
                                                >
                                                    {page.title}
                                                </div>
                                            ))}
                                        </div>
                                    )}
                                </div>
                            </div>
                        </div>
                    </div>
                )}
            </div>
        </div>
    );
}
