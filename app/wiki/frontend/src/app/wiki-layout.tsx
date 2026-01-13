"use client";

import { useState, useEffect, useCallback, useMemo, useRef } from "react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import Fuse from "fuse.js";
import styles from "./layout.module.css";
import ContextMenu from "@/components/ContextMenu";
import RenameModal from "@/components/RenameModal";

interface Folder {
    id: string;
    name: string;
}

interface Page {
    id: string;
    title: string;
    content: string;
    folder_id: string | null;
    parent_id: string | null;
    order: number;
}

interface TreeNode extends Page {
    children: TreeNode[];
}

interface UserDetail {
    id: string;
    email: string;
    full_name: string;
    role_id: string;
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

function SidebarItem({
    node,
    pathname,
    onContextMenu,
    onCreatePage
}: {
    node: TreeNode;
    pathname: string;
    onContextMenu: (e: React.MouseEvent, type: "page", id: string) => void;
    onCreatePage: (folderId?: string, parentId?: string) => void;
}) {
    const [isCollapsed, setIsCollapsed] = useState(true);
    const hasChildren = node.children.length > 0;

    return (
        <li className={styles.navItemWrapper}>
            <div
                className={`${styles.navItem} ${pathname === `/page/${node.id}` ? styles.active : ""}`}
                data-page-id={node.id}
                onContextMenu={(e) => {
                    e.preventDefault();
                    onContextMenu(e, "page", node.id);
                }}
            >
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
                <button
                    className={styles.contextMenuBtn}
                    onClick={(e) => {
                        e.stopPropagation();
                        onContextMenu(e, "page", node.id);
                    }}
                >
                    ⋯
                </button>
                <button
                    className={styles.addChildBtn}
                    onClick={(e) => {
                        e.preventDefault();
                        onCreatePage(node.folder_id || undefined, node.id);
                    }}
                >
                    +
                </button>
            </div>
            {!isCollapsed && hasChildren && (
                <ul className={styles.childList}>
                    {node.children.map(child => (
                        <SidebarItem
                            key={child.id}
                            node={child}
                            pathname={pathname}
                            onContextMenu={onContextMenu}
                            onCreatePage={onCreatePage}
                        />
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
    const [activeFolderId, setActiveFolderId] = useState<string | null>(null);
    const [currentUser, setCurrentUser] = useState<UserDetail | null>(null);
    const [settings, setSettings] = useState<Record<string, string>>({});
    const [tempFolderName, setTempFolderName] = useState("");
    const [renamingFolderId, setRenamingFolderId] = useState<string | null>(null);
    const [renamingPageId, setRenamingPageId] = useState<string | null>(null);
    const [savedFolderId, setSavedFolderId] = useState<string | null>(null);
    const [deletingFolderId, setDeletingFolderId] = useState<string | null>(null);
    const [contextMenu, setContextMenu] = useState<{ x: number; y: number; type: "folder" | "page"; id: string } | null>(null);
    const [renamingAnchor, setRenamingAnchor] = useState<HTMLElement | null>(null);
    const [tempPageTitle, setTempPageTitle] = useState("");
    const searchRef = useRef<HTMLDivElement>(null);
    const pathname = usePathname();
    const router = useRouter();

    const fetchData = useCallback(async (token: string | null) => {
        try {
            const headers: Record<string, string> = {};
            if (token) headers["Authorization"] = `Bearer ${token}`;

            const [pagesRes, foldersRes, userRes, settingsRes] = await Promise.all([
                fetch("http://localhost:8000/pages", { headers }),
                fetch("http://localhost:8000/folders", { headers }),
                fetch(token ? "http://localhost:8000/me" : "data:application/json,{}", { headers }),
                fetch("http://localhost:8000/settings")
            ]);

            if (token && (pagesRes.status === 401 || foldersRes.status === 401 || userRes.status === 401)) {
                localStorage.removeItem("wiki_token");
                router.push("/login");
                return;
            }

            if (pagesRes.ok && foldersRes.ok && userRes.ok) {
                const pagesData = await pagesRes.json();
                setPages(pagesData);
                setFolders(await foldersRes.json());
                setCurrentUser(await userRes.json());

                // Process settings
                const settingsData = await settingsRes.json();
                const settingsMap: Record<string, string> = {};
                settingsData.forEach((s: any) => settingsMap[s.key] = s.value);
                setSettings(settingsMap);

                // Site Name logic
                if (settingsMap.site_name) {
                    document.title = settingsMap.site_name;
                }

                // Home Page logic
                if (pathname === "/" && settingsMap.home_page_id) {
                    const homePage = pagesData.find((p: any) => p.id === settingsMap.home_page_id);
                    if (homePage) {
                        if (homePage.folder_id) setActiveFolderId(homePage.folder_id);
                        router.push(`/page/${homePage.id}`);
                    }
                }
            }
        } catch (error) {
            console.error("Fetch error:", error);
        }
    }, [pathname, router]);

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
        } else if (pathname !== "/login") {
            // Allow unauthenticated fetch for public pages
            fetchData(null);
        }
    }, [pathname, router, fetchData]);

    useEffect(() => {
        const handleClickOutside = (event: MouseEvent) => {
            if (searchRef.current && !searchRef.current.contains(event.target as Node)) {
                setSearchQuery("");
                setSearchResults([]);
            }
        };

        document.addEventListener("mousedown", handleClickOutside);
        return () => {
            document.removeEventListener("mousedown", handleClickOutside);
        };
    }, []);
    const handleCreateFolder = async () => {
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
                body: JSON.stringify({ name: "New Folder" })
            });
            if (res.ok) {
                const newFolder = await res.json();
                await fetchData(token);
                setRenamingFolderId(newFolder.id);
                setTempFolderName("New Folder");

                // Wait for DOM to update, then set anchor to trigger rename modal
                setTimeout(() => {
                    const folderElement = document.querySelector(`[data-folder-id="${newFolder.id}"]`);
                    setRenamingAnchor(folderElement as HTMLElement);
                }, 100);
            } else if (res.status === 401) {
                localStorage.removeItem("wiki_token");
                router.push("/login");
            }
        } catch (error) {
            console.error("Create folder error:", error);
        }
    };


    const handleCreatePage = async (folderId?: string, parentId?: string) => {
        const token = localStorage.getItem("wiki_token");
        if (!token) {
            router.push("/login");
            return;
        }

        try {
            const res = await fetch("http://localhost:8000/pages/", {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                    "Authorization": `Bearer ${token}`
                },
                body: JSON.stringify({
                    title: "New Page",
                    content: "",
                    folder_id: folderId || null,
                    parent_id: parentId || null
                })
            });
            if (res.ok) {
                const newPage = await res.json();
                await fetchData(token);
                setRenamingPageId(newPage.id);
                setTempPageTitle("New Page");

                // Wait for DOM to update, then set anchor to trigger rename modal
                setTimeout(() => {
                    const pageElement = document.querySelector(`[data-page-id="${newPage.id}"]`);
                    setRenamingAnchor(pageElement as HTMLElement);
                }, 100);
            } else if (res.status === 401) {
                localStorage.removeItem("wiki_token");
                router.push("/login");
            }
        } catch (error) {
            console.error("Create page error:", error);
        }
    };

    const handleRenameFolder = async (folderId: string, newName?: string) => {
        const nameToUse = newName || tempFolderName;

        if (!nameToUse.trim()) {
            setRenamingFolderId(null);
            return;
        }

        const token = localStorage.getItem("wiki_token");
        if (!token) return;

        try {
            const res = await fetch(`http://localhost:8000/folders/${folderId}`, {
                method: "PATCH",
                headers: {
                    "Content-Type": "application/json",
                    "Authorization": `Bearer ${token}`
                },
                body: JSON.stringify({ name: nameToUse.trim() })
            });
            if (res.ok) {
                await fetchData(token);
                setRenamingFolderId(null);
                setSavedFolderId(folderId);
                setTimeout(() => setSavedFolderId(null), 2000);
            }
        } catch (error) {
            console.error("Rename folder error:", error);
        }
    };

    const handleRenamePage = async (pageId: string, newName?: string) => {
        const nameToUse = newName || tempPageTitle;

        if (!nameToUse.trim()) {
            setRenamingPageId(null);
            return;
        }

        const token = localStorage.getItem("wiki_token");
        if (!token) return;

        try {
            const res = await fetch(`http://localhost:8000/pages/${pageId}`, {
                method: "PATCH",
                headers: {
                    "Content-Type": "application/json",
                    "Authorization": `Bearer ${token}`
                },
                body: JSON.stringify({ title: nameToUse.trim() })
            });
            if (res.ok) {
                await fetchData(token);
                setRenamingPageId(null);
            }
        } catch (error) {
            console.error("Rename page error:", error);
        }
    };

    const handleDeleteFolder = async (folderId: string) => {
        const token = localStorage.getItem("wiki_token");
        if (!token) return;

        try {
            const res = await fetch(`http://localhost:8000/folders/${folderId}`, {
                method: "DELETE",
                headers: { "Authorization": `Bearer ${token}` }
            });
            if (res.ok) {
                await fetchData(token);
                setRenamingFolderId(null);
                setDeletingFolderId(null);
            }
        } catch (error) {
            console.error("Delete folder error:", error);
        }
    };

    const handleContextMenu = (e: React.MouseEvent, type: "folder" | "page", id: string) => {
        e.preventDefault();
        setContextMenu({ x: e.clientX, y: e.clientY, type, id });
    };

    const handleCopyLink = (id: string, type: "folder" | "page") => {
        const url = type === "page" ? `${window.location.origin}/page/${id}` : `${window.location.origin}/?folder=${id}`;
        navigator.clipboard.writeText(url);
    };

    const handleMoveToTrash = async (id: string, type: "folder" | "page") => {
        const token = localStorage.getItem("wiki_token");
        if (!token) return;

        // For folders, check if there are pages inside
        if (type === "folder") {
            try {
                const res = await fetch(`http://localhost:8000/folders/${id}/page-count`, {
                    headers: { "Authorization": `Bearer ${token}` }
                });
                const data = await res.json();

                if (data.count > 0) {
                    const confirmed = window.confirm(`This folder contains ${data.count} page(s). Move to trash?`);
                    if (!confirmed) return;
                }
            } catch (error) {
                console.error("Error checking page count:", error);
            }
        }

        // Proceed with delete
        const endpoint = type === "folder" ? `http://localhost:8000/folders/${id}` : `http://localhost:8000/pages/${id}`;
        try {
            const res = await fetch(endpoint, {
                method: "DELETE",
                headers: { "Authorization": `Bearer ${token}` }
            });
            if (res.ok) {
                await fetchData(token);
            }
        } catch (error) {
            console.error("Move to trash error:", error);
        }
    };

    const getContextMenuOptions = (type: "folder" | "page", id: string) => {
        if (type === "folder") {
            return [
                {
                    label: "Rename",
                    icon: "✏️",
                    onClick: () => {
                        setRenamingFolderId(id);
                        setTempFolderName(folders.find(f => f.id === id)?.name || "");
                        // Set anchor to the folder element
                        const folderElement = document.querySelector(`[data-folder-id="${id}"]`);
                        setRenamingAnchor(folderElement as HTMLElement);
                    }
                },
                { label: "Share", icon: "👥", onClick: () => console.log("Share folder", id) },
                { label: "Copy Link", icon: "🔗", onClick: () => handleCopyLink(id, "folder") },
                { label: "Move to Trash", icon: "🗑️", onClick: () => handleMoveToTrash(id, "folder"), danger: true }
            ];
        } else {
            return [
                { label: "Rename", icon: "✏️", onClick: () => console.log("Rename page", id) },
                { label: "Share", icon: "👥", onClick: () => console.log("Share page", id) },
                { label: "Copy Link", icon: "🔗", onClick: () => handleCopyLink(id, "page") },
                { label: "Move to Trash", icon: "🗑️", onClick: () => handleMoveToTrash(id, "page"), danger: true }
            ];
        }
    };

    const fuse = useMemo(() => new Fuse(pages, {
        keys: ["title", "content"],
        threshold: 0.3,
        distance: 100,
    }), [pages]);

    const handleSearch = async (query: string) => {
        setSearchQuery(query);
        if (query.length < 2) {
            setSearchResults([]);
            return;
        }

        const results = fuse.search(query).map(r => r.item);
        setSearchResults(results);
    };

    if (!isAuthenticated && pathname !== "/login") {
        return <div className={styles.loading}>Redirecting...</div>;
    }

    if (pathname === "/login") {
        return <div className={styles.loginContainer}>{children}</div>;
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
                        <Link href="/">{settings.site_name || "Wiki"}</Link>
                    </div>
                    <button
                        className={styles.sidebarCollapseBtn}
                        onClick={() => setIsSidebarCollapsed(!isSidebarCollapsed)}
                    >
                        {isSidebarCollapsed ? "→" : "←"}
                    </button>
                </div>
                <div className={styles.searchContainer} ref={searchRef}>
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
                            <li
                                className={`${styles.navItem} ${activeFolderId === null ? styles.activeSpace : ""}`}
                                onClick={() => setActiveFolderId(null)}
                            >
                                🏠 All Pages
                            </li>
                            {folders.map(folder => (
                                <li
                                    key={folder.id}
                                    className={`${styles.navItem} ${activeFolderId === folder.id ? styles.activeSpace : ""}`}
                                    onClick={() => setActiveFolderId(folder.id)}
                                >
                                    <div
                                        className={`${styles.folderItemContent} ${savedFolderId === folder.id ? styles.saved : ""}`}
                                        onContextMenu={(e) => handleContextMenu(e, "folder", folder.id)}
                                        data-folder-id={folder.id}
                                    >
                                        📁 {folder.name}
                                        <button
                                            className={styles.contextMenuBtn}
                                            onClick={(e) => {
                                                e.stopPropagation();
                                                handleContextMenu(e, "folder", folder.id);
                                            }}
                                        >
                                            ⋯
                                        </button>
                                    </div>
                                </li>
                            ))}
                        </ul>
                    </div>

                    <div className={styles.navSection}>
                        <div className={styles.sectionHeader}>
                            <span>PAGES</span>
                            <button className={styles.addBtn} onClick={() => handleCreatePage(activeFolderId || undefined)}>+</button>
                        </div>
                        <ul className={styles.pageList}>
                            {buildTree(pages.filter(p => !activeFolderId || p.folder_id === activeFolderId)).map(node => (
                                <SidebarItem
                                    key={node.id}
                                    node={node}
                                    pathname={pathname}
                                    onContextMenu={handleContextMenu}
                                    onCreatePage={handleCreatePage}
                                />
                            ))}
                        </ul>
                    </div>
                </nav>
                <div className={styles.footer}>
                    {currentUser?.role_id === "superadmin" && (
                        <Link href="/admin" className={styles.adminBtn}>⚙️ Admin Panel</Link>
                    )}
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
            {contextMenu && (
                <ContextMenu
                    x={contextMenu.x}
                    y={contextMenu.y}
                    onClose={() => setContextMenu(null)}
                    options={getContextMenuOptions(contextMenu.type, contextMenu.id)}
                />
            )}
            {renamingFolderId && renamingAnchor && (
                <RenameModal
                    initialValue={tempFolderName}
                    onSave={(newName) => {
                        handleRenameFolder(renamingFolderId, newName);
                        setRenamingAnchor(null);
                    }}
                    onCancel={() => {
                        setRenamingFolderId(null);
                        setRenamingAnchor(null);
                    }}
                    anchorElement={renamingAnchor}
                />
            )}
            {renamingPageId && renamingAnchor && (
                <RenameModal
                    initialValue={tempPageTitle}
                    onSave={(newName) => {
                        handleRenamePage(renamingPageId, newName);
                        setRenamingAnchor(null);
                    }}
                    onCancel={() => {
                        setRenamingPageId(null);
                        setRenamingAnchor(null);
                    }}
                    anchorElement={renamingAnchor}
                />
            )}
        </div>
    );
}
