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
    const [bannerUrl, setBannerUrl] = useState<string | null>(null);
    const [isPublic, setIsPublic] = useState(false);
    const [showBannerInput, setShowBannerInput] = useState(false);
    const [tempBannerUrl, setTempBannerUrl] = useState("");
    const router = useRouter();

    const fetchPage = useCallback(async () => {
        const token = localStorage.getItem("wiki_token");
        // No redirect for public pages

        try {
            const headers: any = {};
            if (token) headers["Authorization"] = `Bearer ${token}`;

            const response = await fetch(`http://localhost:8000/pages/${id}`, {
                headers: headers
            });
            if (response.ok) {
                const data = await response.json();
                setPage(data);
                setTitle(data.title);
                setBannerUrl(data.banner_url);
                setIsPublic(data.is_public);
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
        debounce(async (updatedData: { title?: string, content?: string, banner_url?: string | null, is_public?: boolean }) => {
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

    const handleAddBanner = () => {
        if (tempBannerUrl) {
            setBannerUrl(tempBannerUrl);
            debouncedSave({ banner_url: tempBannerUrl });
            setShowBannerInput(false);
            setTempBannerUrl("");
        }
    };

    const handleTogglePublic = () => {
        const newVal = !isPublic;
        setIsPublic(newVal);
        debouncedSave({ is_public: newVal });
    };

    const handleRemoveBanner = () => {
        setBannerUrl(null);
        debouncedSave({ banner_url: null });
    };

    if (loading) return <div className={styles.pageContainer}>Loading...</div>;
    if (!page) return <div className={styles.pageContainer}>Page not found</div>;

    return (
        <div className={styles.pageContainer}>
            {bannerUrl && (
                <div className={styles.bannerWrapper}>
                    <img src={bannerUrl} alt="Banner" className={styles.bannerImage} />
                    {isEditing && (
                        <div className={styles.bannerActions}>
                            <button onClick={() => setShowBannerInput(true)} className={styles.changeBannerBtn}>Change</button>
                            <button onClick={handleRemoveBanner} className={styles.removeBannerBtn}>Remove</button>
                        </div>
                    )}
                </div>
            )}
            <div className={styles.mainContent}>
                {isEditing && showBannerInput && (
                    <div className={styles.bannerInputOverlay}>
                        <input
                            value={tempBannerUrl}
                            onChange={(e) => setTempBannerUrl(e.target.value)}
                            placeholder="Paste banner image URL..."
                            className={styles.bannerUrlInput}
                            autoFocus
                        />
                        <button onClick={handleAddBanner} className={styles.saveBannerBtn}>Set Banner</button>
                        <button onClick={() => setShowBannerInput(false)} className={styles.cancelBannerBtn}>Cancel</button>
                    </div>
                )}
                {!bannerUrl && isEditing && !showBannerInput && (
                    <button onClick={() => setShowBannerInput(true)} className={styles.addBannerBtn}>🖼️ Add Banner</button>
                )}
                <header className={styles.header}>
                    <div className={styles.titleSection}>
                        {isEditing ? (
                            <input
                                className={styles.titleInput}
                                value={title}
                                onChange={(e) => handleTitleChange(e.target.value)}
                            />
                        ) : (
                            <h1 className={styles.title}>{title}</h1>
                        )}
                        {isEditing && (
                            <label className={styles.publicToggle}>
                                <input
                                    type="checkbox"
                                    checked={isPublic}
                                    onChange={handleTogglePublic}
                                />
                                🌍 Public
                            </label>
                        )}
                    </div>
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
        </div>
    );
}
