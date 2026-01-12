"use client";

import { useState, useEffect, useCallback } from "react";
import { useRouter } from "next/navigation";
import styles from "./admin.module.css";

interface UserDetail {
    id: string;
    email: string;
    full_name: string;
    role_id: string;
}

export default function AdminPanel() {
    const [users, setUsers] = useState<UserDetail[]>([]);
    const [roles, setRoles] = useState<any[]>([]);
    const [pages, setPages] = useState<any[]>([]);
    const [settings, setSettings] = useState<any[]>([]);
    const [activeTab, setActiveTab] = useState("users");
    const [loading, setLoading] = useState(true);
    const [editingUser, setEditingUser] = useState<UserDetail | null>(null);
    const router = useRouter();

    const fetchAdminData = useCallback(async (token: string) => {
        try {
            const [usersRes, rolesRes, pagesRes, settingsRes] = await Promise.all([
                fetch("http://localhost:8000/admin/users", {
                    headers: { "Authorization": `Bearer ${token}` }
                }),
                fetch("http://localhost:8000/admin/roles", {
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
                fetchAdminData(token!);
            }
        } catch (error) {
            console.error("Setting update error:", error);
        }
    };

    if (loading) return <div className={styles.adminContainer}>Loading...</div>;

    return (
        <div className={styles.adminContainer}>
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
                    Roles
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
                            <span>Role</span>
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
                                        <select
                                            value={editingUser.role_id}
                                            onChange={(e) => setEditingUser({ ...editingUser, role_id: e.target.value })}
                                            className={styles.roleSelect}
                                        >
                                            {roles.map(r => <option key={r.id} value={r.id}>{r.name}</option>)}
                                        </select>
                                    ) : (
                                        <span className={styles.roleBadge}>{user.role_id}</span>
                                    )}
                                </div>
                                <div className={styles.actions}>
                                    {editingUser?.id === user.id ? (
                                        <>
                                            <button onClick={() => handleUpdateUser(user.id, editingUser)} className={styles.saveBtn}>Save</button>
                                            <button onClick={() => setEditingUser(null)} className={styles.cancelBtn}>Cancel</button>
                                        </>
                                    ) : (
                                        <button onClick={() => setEditingUser(user)} className={styles.editBtn}>Edit</button>
                                    )}
                                </div>
                            </div>
                        ))}
                    </div>
                )}

                {activeTab === "roles" && (
                    <div className={styles.roleList}>
                        <div className={styles.tableHeader}>
                            <span>Role ID</span>
                            <span>Role Name</span>
                        </div>
                        {roles.map(role => (
                            <div key={role.id} className={styles.tableRow}>
                                <span>{role.id}</span>
                                <span>{role.name}</span>
                            </div>
                        ))}
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
                                />
                            </div>
                        </div>
                        <div className={styles.settingItem}>
                            <h3>Navigation</h3>
                            <div className={styles.inputGroup}>
                                <label>Home Page</label>
                                <select
                                    value={settings.find(s => s.key === "home_page_id")?.value || ""}
                                    onChange={(e) => handleUpdateSetting("home_page_id", e.target.value)}
                                >
                                    <option value="">Default (Welcome)</option>
                                    {pages.map(p => <option key={p.id} value={p.id}>{p.title}</option>)}
                                </select>
                            </div>
                        </div>
                        <div className={styles.settingItem}>
                            <h3>Access Control</h3>
                            <p>Global public access settings can be managed here. Individually mark pages/folders as public to allow unauthenticated view.</p>
                        </div>
                    </div>
                )}
            </div>
        </div>
    );
}
