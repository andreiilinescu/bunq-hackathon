import React from "react";
import styles from "./Message.module.scss";
const Message = ({ message, role }) => {
	// Determine alignment style based on role

	return (
		<div className={styles.messageContainer}>
			{role === "user" ? (
				<div className={`${styles.userMessage} ${styles.message} `}>
					<p className={styles.messageP}>{message}</p>
				</div>
			) : (
				<div
					className={`${styles.assistantMessage}  ${styles.message}  `}
				>
					<p className={styles.messageP}>{message}</p>
				</div>
			)}
		</div>
	);
};

export default Message;
