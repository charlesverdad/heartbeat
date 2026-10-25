"use client";

import styles from "./page.module.css";
import Link from "next/link";

export default function Home() {
  return (
    <div className={styles.homeContainer}>
      <h1>Welcome to the Wiki</h1>
      <p>Select a page from the sidebar to get started, or create a new one.</p>

      <div className={styles.quickActions}>
        <Link href="/page/new" className={styles.actionCard}>
          <h3>New Page</h3>
          <p>Create a new document in the root or a folder.</p>
        </Link>
        <Link href="/search" className={styles.actionCard}>
          <h3>Search</h3>
          <p>Search across all organization documents.</p>
        </Link>
      </div>
    </div>
  );
}
