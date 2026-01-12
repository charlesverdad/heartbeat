"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import styles from "./admin.module.css";

export default function AdminPanel() {
    const [users, setUsers] = useState<any[]>([]);
    const [roles, setRoles] = useState<any[]>([]);
    const [activeTab, setActiveTab] = useState("users");
    const [loading, setLoading] = useState(true);
    const router = useRouter();

    useEffect(() => {
        const token = localStorage.getItem("wiki_token");
        if (!token) {
            router.push("/login");
            return;
        }
        fetchAdminData(token);
    }, [router]);

    const fetchAdminData = async (token: string) => {
        try {
            const [usersRes, rolesRes] = await Promise.all([
                fetch("http://localhost:8000/admin/users", {
                    headers: { "Authorization": `Bearer ${token}` }
                }),
                fetch("http://localhost:8000/admin/roles", {
                    headers: { "Authorization": `Bearer ${token}` }
                })
            ]);

            if (usersRes.status === 403) {
                alert("Only Super Admins can access this panel");
                router.push("/");
                return;
            }

            if (usersRes.ok && rolesRes.ok) {
                setUsers(await usersRes.json());
                setRoles(await rolesRes.json());
            }
        } catch (error) {
            console.error("Fetch error:", error);
        } finally {
            setLoading(false);
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
                        </div>
                        {users.map(user => (
                            <div key={user.id} className={styles.tableRow}>
                                <span>{user.email}</span>
                                <span>{user.full_name}</span>
                                <span className={styles.roleBadge}>{user.role_id}</span>
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
                            <h3>Theme</h3>
                            <p>Current Theme: Light (Minimalist)</p>
                            <button className={styles.toggleBtn}>Toggle Dark Mode (Preview)</button>
                        </div>
                        <div className={styles.settingItem}>
                            <h3>Layout</h3>
                            <p>Sidebar Position: Left</p>
                            <button className={styles.toggleBtn}>Change to Right</button>
                        </div>
                    </div>
                )}
            </div>
        </div>
    );
}
