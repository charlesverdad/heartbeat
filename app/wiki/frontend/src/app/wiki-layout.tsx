"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import styles from "./layout.module.css";

interface Folder {
    id: string;
    name: string;
}

interface Page {
    id: string;
    title: string;
    folder_id: string | null;
    parent_id: string | null;
    order: number;
}

interface TreeNode extends Page {
    children: TreeNode[];
}

function buildTree(items: Page[]): TreeNode[] {
    const itemMap = new Map<string, TreeNode>();
    items.forEach(item => itemMap.set(item.id, { ...item, children: [] }));

    const rootNodes: TreeNode[] = [];
    itemMap.forEach(node => {
        if (node.parent_id && itemMap.has(node.parent_id)) {
            itemMap.get(node.parent_id)!.children.push(node);
        } else {
            rootNodes.push(node);
        }
    });

    // Sort by order
    const sortNodes = (nodes: TreeNode[]) => {
        nodes.sort((a, b) => a.order - b.order);
        nodes.forEach(node => sortNodes(node.children));
    };
    sortNodes(rootNodes);

    return rootNodes;
}

function SidebarItem({ node, pathname }: { node: TreeNode, pathname: string }) {
    const [isCollapsed, setIsCollapsed] = useState(true);
    const hasChildren = node.children.length > 0;

    return (
        <li className={styles.navItemWrapper}>
            <div className={`${styles.navItem} ${pathname === `/page/${node.id}` ? styles.active : ""}`}>
                {hasChildren && (
                    <button
                        className={styles.collapseToggle}
                        onClick={() => setIsCollapsed(!isCollapsed)}
                    >
                        {isCollapsed ? "▶" : "▼"}
                    </button>
                )}
                <Link href={`/page/${node.id}`} className={styles.pageLink}>
                    {node.title}
                </Link>
                <Link href={`/page/new?parent_id=${node.id}`} className={styles.addChildBtn}>+</Link>
            </div>
            {!isCollapsed && hasChildren && (
                <ul className={styles.childList}>
                    {node.children.map(child => (
                        <SidebarItem key={child.id} node={child} pathname={pathname} />
                    ))}
                </ul>
            )}
        </li>
    );
}
export default function WikiLayout({ children }: { children: React.ReactNode }) {
    const [folders, setFolders] = useState<Folder[]>([]);
    const [pages, setPages] = useState<Page[]>([]);
    const [isAuthenticated, setIsAuthenticated] = useState(false);
    const pathname = usePathname();
    const router = useRouter();

    useEffect(() => {
        const token = localStorage.getItem("wiki_token");
        if (!token && pathname !== "/login") {
            router.push("/login");
            return;
        }

        if (token) {
            setIsAuthenticated(true);
            fetchData(token);
        }
    }, [pathname, router]);

    const fetchData = async (token: string) => {
        try {
            const res = await fetch("http://localhost:8000/pages", {
                headers: {
                    "Authorization": `Bearer ${token}`
                }
            });
            if (res.status === 401) {
                localStorage.removeItem("wiki_token");
                router.push("/login");
                return;
            }
            const data = await res.json();
            setPages(data);

            // For now, mock folders until folders API is implemented
            setFolders([
                { id: "root", name: "General" }
            ]);
        } catch (error) {
            console.error("Fetch error:", error);
        }
    };

    if (!isAuthenticated && pathname !== "/login") {
        return <div className={styles.loading}>Redirecting...</div>;
    }

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
                        <div className={styles.sectionHeader}>
                            <h3>Folders</h3>
                            <button className={styles.addBtn} title="Add Folder">+</button>
                        </div>
                        <ul>
                            {folders.map(folder => (
                                <li key={folder.id}>
                                    <Link href={`/folder/${folder.id}`}>{folder.name}</Link>
                                </li>
                            ))}
                        </ul>
                    </div>
                    <div className={styles.section}>
                        <div className={styles.sectionHeader}>
                            <h3>Pages</h3>
                            <Link href="/page/new" className={styles.addBtn} title="Add Page">+</Link>
                        </div>
                        <ul>
                            {buildTree(pages).map(node => (
                                <SidebarItem key={node.id} node={node} pathname={pathname} />
                            ))}
                        </ul>
                    </div>
                </nav>
                <div className={styles.footer}>
                    <button className={styles.exportBtn}>Export .zip</button>
                    <button
                        className={styles.logoutBtn}
                        onClick={() => {
                            localStorage.removeItem("wiki_token");
                            router.push("/login");
                        }}
                    >
                        Logout
                    </button>
                </div>
            </aside>
            <main className={styles.main}>
                {children}
            </main>
        </div>
    );
}
