"use client";

import { useState, useEffect, Suspense } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import styles from "./page.module.css";

function NewPageForm() {
    const [title, setTitle] = useState("");
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState("");
    const router = useRouter();
    const searchParams = useSearchParams();
    const parentId = searchParams.get("parent_id");

    useEffect(() => {
        const token = localStorage.getItem("wiki_token");
        if (!token) {
            router.push("/login");
        }
    }, [router]);

    const handleCreate = async () => {
        if (!title.trim()) return;
        setLoading(true);
        setError("");

        try {
            const token = localStorage.getItem("wiki_token");
            const response = await fetch("http://localhost:8000/pages/", {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                    "Authorization": `Bearer ${token}`
                },
                body: JSON.stringify({
                    title: title,
                    content: "<h1>" + title + "</h1><p>Start writing here...</p>",
                    parent_id: parentId || null
                })
            });

            if (response.ok) {
                const data = await response.json();
                router.push(`/page/${data.id}`);
            } else {
                const errData = await response.json();
                setError(errData.detail || "Failed to create page");
            }
        } catch (err) {
            setError("Connection error");
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className={styles.newPageContainer}>
            <h1>Create {parentId ? "Subpage" : "New Page"}</h1>
            <div className={styles.formGroup}>
                <label>Title</label>
                <input
                    type="text"
                    value={title}
                    onChange={(e) => setTitle(e.target.value)}
                    placeholder="Enter page title..."
                    autoFocus
                />
            </div>
            {error && <p className={styles.error}>{error}</p>}
            <button
                onClick={handleCreate}
                className={styles.createBtn}
                disabled={loading || !title.trim()}
            >
                {loading ? "Creating..." : "Create Page"}
            </button>
        </div>
    );
}

export default function NewPage() {
    return (
        <Suspense fallback={<div>Loading...</div>}>
            <NewPageForm />
        </Suspense>
    );
}
