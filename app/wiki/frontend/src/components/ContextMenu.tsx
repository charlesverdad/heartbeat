import { useEffect, useRef } from "react";
import styles from "./ContextMenu.module.css";

interface ContextMenuProps {
    x: number;
    y: number;
    onClose: () => void;
    options: {
        label: string;
        icon?: string;
        onClick: () => void;
        danger?: boolean;
    }[];
}

export default function ContextMenu({ x, y, onClose, options }: ContextMenuProps) {
    const menuRef = useRef<HTMLDivElement>(null);

    useEffect(() => {
        const handleEscape = (e: KeyboardEvent) => {
            if (e.key === "Escape") onClose();
        };

        document.addEventListener("keydown", handleEscape);
        return () => document.removeEventListener("keydown", handleEscape);
    }, [onClose]);

    return (
        <>
            <div className={styles.overlay} onClick={onClose} />
            <div
                ref={menuRef}
                className={styles.contextMenu}
                style={{ top: y, left: x }}
            >
                {options.map((option, idx) => (
                    <button
                        key={idx}
                        className={`${styles.menuItem} ${option.danger ? styles.danger : ""}`}
                        onClick={() => {
                            option.onClick();
                            onClose();
                        }}
                    >
                        {option.icon && <span className={styles.icon}>{option.icon}</span>}
                        {option.label}
                    </button>
                ))}
            </div>
        </>
    );
}
