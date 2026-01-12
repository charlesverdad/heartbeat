"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import styles from "./page.module.css";

export default function NewPage() {
    const [title, setTitle] = useState("");
    const router = useRouter();

    const handleCreate = () => {
        // Mock create
        console.log("Creating page:", title);
        router.push("/page/new-id");
    };

    return (
        <div className={styles.newPageContainer}>
            <h1>Create New Page</h1>
            <div className={styles.formGroup}>
                <label>Title</label>
                <input
                    type="text"
                    value={title}
                    onChange={(e) => setTitle(e.target.value)}
                    placeholder="Enter page title..."
                />
            </div>
            <button onClick={handleCreate} className={styles.createBtn}>Create Page</button>
        </div>
    );
}
