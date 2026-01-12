"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import styles from "./layout.module.css";

interface Folder {
    id: string;
    name: string;
    children: any[];
}

interface Page {
    id: string;
    title: string;
    folder_id: string | null;
}

export default function WikiLayout({ children }: { children: React.ReactNode }) {
    const [folders, setFolders] = useState<Folder[]>([]);
    const [pages, setPages] = useState<Page[]>([]);
    const pathname = usePathname();

    useEffect(() => {
        // Fetch folders and pages for the sidebar
        // Mocking for now
        setFolders([
            { id: "1", name: "Engineering", children: [] },
            { id: "2", name: "Marketing", children: [] },
        ]);
        setPages([
            { id: "p1", title: "Overview", folder_id: null },
            { id: "p2", title: "API Docs", folder_id: "1" },
        ]);
    }, []);

    return (
        <div className={styles.container}>
            <aside className={styles.sidebar}>
                <div className={styles.logo}>
                    <Link href="/">Wiki</Link>
                </div>
                <div className={styles.searchContainer}>
                    <input type="text" placeholder="Search pages..." className={styles.searchInput} />
                </div>
                <nav className={styles.nav}>
                    <div className={styles.section}>
                        <h3>Folders</h3>
                        <ul>
                            {folders.map(folder => (
                                <li key={folder.id}>
                                    <Link href={`/folder/${folder.id}`}>{folder.name}</Link>
                                </li>
                            ))}
                        </ul>
                    </div>
                    <div className={styles.section}>
                        <h3>Recent Pages</h3>
                        <ul>
                            {pages.map(page => (
                                <li key={page.id}>
                                    <Link href={`/page/${page.id}`}>{page.title}</Link>
                                </li>
                            ))}
                        </ul>
                    </div>
                </nav>
                <div className={styles.footer}>
                    <button className={styles.exportBtn}>Export .zip</button>
                </div>
            </aside>
            <main className={styles.main}>
                {children}
            </main>
        </div>
    );
}
