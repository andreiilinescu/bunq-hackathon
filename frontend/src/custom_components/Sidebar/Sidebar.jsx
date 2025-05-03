import React from "react";
import { ThreadList } from "@/components/thread-list";
import styles from "./Sidebar.module.scss";

const Sidebar = () => (
	<aside className={styles.sidebar}>
		<ThreadList /> {/* comes with new‑thread button built‑in */}
	</aside>
);

export default Sidebar;
