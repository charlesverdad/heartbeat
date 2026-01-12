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
    const [isSidebarCollapsed, setIsSidebarCollapsed] = useState(false);
    const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false);
    const [searchQuery, setSearchQuery] = useState("");
    const [searchResults, setSearchResults] = useState<Page[]>([]);
    const [isSearching, setIsSearching] = useState(false);
    const pathname = usePathname();
    const router = useRouter();

    useEffect(() => {
        setIsMobileMenuOpen(false); // Close mobile menu on navigation
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
            const [pagesRes, foldersRes] = await Promise.all([
                fetch("http://localhost:8000/pages", {
                    headers: { "Authorization": `Bearer ${token}` }
                }),
                fetch("http://localhost:8000/folders", {
                    headers: { "Authorization": `Bearer ${token}` }
                })
            ]);

            if (pagesRes.status === 401 || foldersRes.status === 401) {
                localStorage.removeItem("wiki_token");
                router.push("/login");
                return;
            }

            if (pagesRes.ok && foldersRes.ok) {
                setPages(await pagesRes.json());
                setFolders(await foldersRes.json());
            }
        } catch (error) {
            console.error("Fetch error:", error);
        }
    };

    const handleCreateFolder = async () => {
        const name = prompt("Enter folder name:");
        if (!name) return;

        const token = localStorage.getItem("wiki_token");
        if (!token) {
            router.push("/login");
            return;
        }

        try {
            const res = await fetch("http://localhost:8000/folders", {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                    "Authorization": `Bearer ${token}`
                },
                body: JSON.stringify({ name })
            });
            if (res.ok) {
                fetchData(token);
            } else if (res.status === 401) {
                localStorage.removeItem("wiki_token");
                router.push("/login");
            } else {
                console.error("Failed to create folder:", await res.text());
            }
        } catch (error) {
            console.error("Create folder error:", error);
        }
    };

    const handleSearch = async (query: string) => {
        setSearchQuery(query);
        if (query.length < 2) {
            setSearchResults([]);
            setIsSearching(false);
            return;
        }

        setIsSearching(true);
        const token = localStorage.getItem("wiki_token");
        try {
            const res = await fetch(`http://localhost:8000/pages/search?q=${encodeURIComponent(query)}`, {
                headers: { "Authorization": `Bearer ${token}` }
            });
            if (res.ok) {
                setSearchResults(await res.json());
            }
        } catch (error) {
            console.error("Search error:", error);
        } finally {
            setIsSearching(false);
        }
    };

    if (!isAuthenticated && pathname !== "/login") {
        return <div className={styles.loading}>Redirecting...</div>;
    }

    return (
        <div className={`${styles.container} ${isSidebarCollapsed ? styles.collapsed : ""} ${isMobileMenuOpen ? styles.mobileOpen : ""}`}>
            <button
                className={styles.mobileToggle}
                onClick={() => setIsMobileMenuOpen(!isMobileMenuOpen)}
            >
                ☰
            </button>
            <aside className={styles.sidebar}>
                <div className={styles.sidebarHeader}>
                    <div className={styles.logo}>
                        <Link href="/">Wiki</Link>
                    </div>
                    <button
                        className={styles.sidebarCollapseBtn}
                        onClick={() => setIsSidebarCollapsed(!isSidebarCollapsed)}
                    >
                        {isSidebarCollapsed ? "→" : "←"}
                    </button>
                </div>
                <div className={styles.searchContainer}>
                    <input
                        type="text"
                        placeholder="Search pages..."
                        className={styles.searchInput}
                        value={searchQuery}
                        onChange={(e) => handleSearch(e.target.value)}
                    />
                    {searchQuery.length > 0 && (
                        <div className={styles.searchResults}>
                            {isSearching ? (
                                <div className={styles.searchStatus}>Searching...</div>
                            ) : searchResults.length > 0 ? (
                                searchResults.map(p => (
                                    <Link
                                        key={p.id}
                                        href={`/page/${p.id}`}
                                        className={styles.searchResultItem}
                                        onClick={() => setSearchQuery("")}
                                    >
                                        📄 {p.title}
                                    </Link>
                                ))
                            ) : (
                                <div className={styles.searchStatus}>No results.</div>
                            )}
                        </div>
                    )}
                </div>
                <nav className={styles.nav}>
                    <div className={styles.navSection}>
                        <div className={styles.sectionHeader}>
                            <span>FOLDERS</span>
                            <button className={styles.addBtn} onClick={handleCreateFolder}>+</button>
                        </div>
                        <ul className={styles.folderList}>
                            {folders.map(folder => (
                                <li key={folder.id} className={styles.navItem}>
                                    📁 {folder.name}
                                </li>
                            ))}
                        </ul>
                    </div>

                    <div className={styles.navSection}>
                        <div className={styles.sectionHeader}>
                            <span>PAGES</span>
                            <Link href="/page/new" className={styles.addBtn}>+</Link>
                        </div>
                        <ul className={styles.pageList}>
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
