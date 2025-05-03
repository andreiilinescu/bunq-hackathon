import React from "react";
import { Thread } from "@/components/thread";
import styles from "./ChatWindow.module.scss";

const ChatWindow = () => (
	<main className={styles.chatWindow}>
		<Thread /> {/* full message list + composer */}
	</main>
);

export default ChatWindow;
