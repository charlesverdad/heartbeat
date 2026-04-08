import { useEffect, useRef, useState } from "react";
import styles from "./RenameModal.module.css";

interface RenameModalProps {
    initialValue: string;
    onSave: (newName: string) => void;
    onCancel: () => void;
    anchorElement: HTMLElement | null;
}

export default function RenameModal({ initialValue, onSave, onCancel, anchorElement }: RenameModalProps) {
    const [value, setValue] = useState(initialValue);
    const modalRef = useRef<HTMLDivElement>(null);
    const inputRef = useRef<HTMLInputElement>(null);

    useEffect(() => {
        // Focus input on mount
        inputRef.current?.focus();
        inputRef.current?.select();

        // Position modal near anchor element
        if (anchorElement && modalRef.current) {
            const rect = anchorElement.getBoundingClientRect();
            modalRef.current.style.top = `${rect.bottom + 8}px`;
            modalRef.current.style.left = `${rect.left}px`;
        }

        // Close on Escape
        const handleEscape = (e: KeyboardEvent) => {
            if (e.key === "Escape") onCancel();
        };
        document.addEventListener("keydown", handleEscape);
        return () => document.removeEventListener("keydown", handleEscape);
    }, [anchorElement, onCancel]);

    const handleSubmit = (e: React.FormEvent) => {
        e.preventDefault();
        if (value.trim()) {
            onSave(value.trim());
        }
    };

    return (
        <>
            <div className={styles.overlay} onClick={onCancel} />
            <div ref={modalRef} className={styles.modal}>
                <form onSubmit={handleSubmit}>
                    <label className={styles.label}>Rename</label>
                    <input
                        ref={inputRef}
                        type="text"
                        value={value}
                        onChange={(e) => setValue(e.target.value)}
                        className={styles.input}
                        placeholder="Enter name..."
                    />
                    <div className={styles.actions}>
                        <button type="button" onClick={onCancel} className={styles.cancelBtn}>
                            Cancel
                        </button>
                        <button type="submit" className={styles.saveBtn}>
                            Save
                        </button>
                    </div>
                </form>
            </div>
        </>
    );
}
