"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import styles from "./login.module.css";

export default function LoginPage() {
    const [email, setEmail] = useState("");
    const [password, setPassword] = useState("");
    const [error, setError] = useState("");
    const [loading, setLoading] = useState(false);
    const router = useRouter();

    const handleLogin = async (e: React.FormEvent) => {
        e.preventDefault();
        setLoading(true);
        setError("");

        try {
            const formData = new FormData();
            formData.append("username", email);
            formData.append("password", password);

            const response = await fetch("http://localhost:8000/token", {
                method: "POST",
                body: formData,
            });

            if (response.ok) {
                const data = await response.json();
                localStorage.setItem("wiki_token", data.access_token);
                router.push("/");
            } else {
                const errData = await response.json();
                setError(errData.detail || "Login failed");
            }
        } catch (err) {
            setError("Connection error");
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className={styles.loginContainer}>
            <div className={styles.loginCard}>
                <h1>Wiki Login</h1>
                <p>Sign in to your organization's knowledgebase</p>

                <form onSubmit={handleLogin} className={styles.loginForm}>
                    <div className={styles.field}>
                        <label>Email</label>
                        <input
                            type="email"
                            value={email}
                            onChange={(e) => setEmail(e.target.value)}
                            required
                        />
                    </div>
                    <div className={styles.field}>
                        <label>Password</label>
                        <input
                            type="password"
                            value={password}
                            onChange={(e) => setPassword(e.target.value)}
                            required
                        />
                    </div>
                    {error && <p className={styles.errorMessage}>{error}</p>}
                    <button type="submit" className={styles.loginBtn} disabled={loading}>
                        {loading ? "Signing in..." : "Login"}
                    </button>
                </form>

                <div className={styles.divider}>OR</div>

                <button className={styles.googleBtn} onClick={() => { }}>
                    Sign in with Google
                </button>
            </div>
        </div>
    );
}
