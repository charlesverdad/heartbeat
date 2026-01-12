"use client";

import { useState, useEffect, useCallback, use } from "react";
import { useRouter } from "next/navigation";
import dynamic from "next/dynamic";
import styles from "./page.module.css";
import { debounce } from "lodash";

// Import Editor dynamically to avoid SSR issues with BlockNote
const Editor = dynamic(() => import("@/components/Editor"), { ssr: false });

export default function PageDetail({ params }: { params: Promise<{ id: string }> }) {
    const { id } = use(params);
    const [page, setPage] = useState<any>(null);
    const [isEditing, setIsEditing] = useState(false);
    const [loading, setLoading] = useState(true);
    const [title, setTitle] = useState("");
    const router = useRouter();

    const fetchPage = useCallback(async () => {
        const token = localStorage.getItem("wiki_token");
        if (!token) {
            router.push("/login");
            return;
        }

        try {
            const response = await fetch(`http://localhost:8000/pages/${id}`, {
                headers: {
                    "Authorization": `Bearer ${token}`
                }
            });
            if (response.ok) {
                const data = await response.json();
                setPage(data);
                setTitle(data.title);
            } else if (response.status === 401) {
                router.push("/login");
            } else {
                setPage(null);
            }
        } catch (error) {
            console.error("Failed to fetch page:", error);
        } finally {
            setLoading(false);
        }
    }, [id, router]);

    useEffect(() => {
        fetchPage();
    }, [fetchPage]);

    // Debounced save function
    const debouncedSave = useCallback(
        debounce(async (updatedData: { title?: string, content?: string }) => {
            const token = localStorage.getItem("wiki_token");
            if (!token) return;

            try {
                const response = await fetch(`http://localhost:8000/pages/${id}`, {
                    method: "PUT",
                    headers: {
                        "Content-Type": "application/json",
                        "Authorization": `Bearer ${token}`
                    },
                    body: JSON.stringify(updatedData),
                });
                if (response.ok) {
                    console.log("Auto-saved");
                }
            } catch (error) {
                console.error("Persistence error:", error);
            }
        }, 1000),
        [id]
    );

    const handleContentChange = (html: string) => {
        if (isEditing) {
            debouncedSave({ content: html });
        }
    };

    const handleTitleChange = (newTitle: string) => {
        setTitle(newTitle);
        debouncedSave({ title: newTitle });
    };

    if (loading) return <div className={styles.pageContainer}>Loading...</div>;
    if (!page) return <div className={styles.pageContainer}>Page not found</div>;

    return (
        <div className={styles.pageContainer}>
            <header className={styles.header}>
                {isEditing ? (
                    <input
                        className={styles.titleInput}
                        value={title}
                        onChange={(e) => handleTitleChange(e.target.value)}
                    />
                ) : (
                    <h1 className={styles.title}>{title}</h1>
                )}
                <div className={styles.actions}>
                    <button
                        onClick={() => setIsEditing(!isEditing)}
                        className={isEditing ? styles.doneBtn : styles.editBtn}
                    >
                        {isEditing ? "Close Editor" : "Edit Page"}
                    </button>
                </div>
            </header>
            <div className={styles.content}>
                <Editor
                    initialContent={page.content}
                    editable={isEditing}
                    onChange={handleContentChange}
                />
            </div>
        </div>
    );
}
