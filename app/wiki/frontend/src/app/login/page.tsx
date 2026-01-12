"use client";

import styles from "./login.module.css";

export default function LoginPage() {
    const handleGoogleLogin = () => {
        // In a real app, this would redirect to Google OAuth
        window.location.href = "http://localhost:8000/auth/google";
    };

    return (
        <div className={styles.loginContainer}>
            <div className={styles.loginCard}>
                <h1>Wiki Login</h1>
                <p>Sign in to your organization's knowledgebase</p>
                <button className={styles.googleBtn} onClick={handleGoogleLogin}>
                    Sign in with Google
                </button>
            </div>
        </div>
    );
}
