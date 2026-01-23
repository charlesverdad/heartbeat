"use client";

import "@blocknote/core/fonts/inter.css";
import { useCreateBlockNote } from "@blocknote/react";
import { BlockNoteView } from "@blocknote/mantine";
import "@blocknote/mantine/style.css";
import { useEffect } from "react";

interface EditorProps {
    initialContent?: string;
    onChange?: (html: string) => void;
    editable?: boolean;
}

export default function Editor({ initialContent, onChange, editable = true }: EditorProps) {
    // Initialize the editor
    const editor = useCreateBlockNote();

    useEffect(() => {
        if (initialContent && editor) {
            const blocks = editor.tryParseHTMLToBlocks(initialContent);
            editor.replaceBlocks(editor.document, blocks);
        }
    }, [editor, initialContent]); // Run on mount/editor init/initialContent change

    return (
        <div style={{ minHeight: "200px" }}>
            <BlockNoteView
                editor={editor}
                editable={editable}
                onChange={() => {
                    if (onChange) {
                        // Get HTML representation
                        const html = editor.blocksToFullHTML(editor.document);
                        // blocksToFullHTML might return a Promise in some versions, but if it's a string synchronously:
                        if (html && typeof (html as any).then === "function") {
                            (html as any).then(onChange);
                        }
                    }
                }}
                theme="light"
            />
        </div>
    );
}
