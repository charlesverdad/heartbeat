"use client";

import { useState, useEffect } from "react";
import dynamic from "next/dynamic";
import styles from "./page.module.css";

// Import Editor dynamically to avoid SSR issues with BlockNote
const Editor = dynamic(() => import("@/components/Editor"), { ssr: false });

export default function PageDetail({ params }: { params: { id: string } }) {
    const [page, setPage] = useState<any>(null);
    const [isEditing, setIsEditing] = useState(false);

    useEffect(() => {
        // Fetch page data
        setPage({
            id: params.id,
            title: "Sample Wiki Page",
            content: "<h1>Welcome</h1><p>This is a sample page content.</p>",
        });
    }, [params.id]);

    if (!page) return <div>Loading...</div>;

    return (
        <div className={styles.pageContainer}>
            <header className={styles.header}>
                <h1 className={styles.title}>{page.title}</h1>
                <div className={styles.actions}>
                    <button onClick={() => setIsEditing(!isEditing)}>
                        {isEditing ? "Done" : "Edit"}
                    </button>
                </div>
            </header>
            <div className={styles.content}>
                <Editor
                    initialContent={page.content}
                    editable={isEditing}
                    onChange={(html) => console.log("Content changed:", html)}
                />
            </div>
        </div>
    );
}
