import React from "react";
import styles from "./Message.module.scss";
import AudioPlayer from "../AudioPlayer/AudioPlayer";
const Message = ({ message, role, audio }) => {
	// Determine alignment style based on role

	return (
		<div className={styles.messageContainer}>
			{role === "user" ? (
				<>
					<div className={`${styles.userMessage} ${styles.message}`}>
						{audio !== "none" && (
							<div className={styles.audioPlayerContainer}>
								<AudioPlayer audioBlob={audio} />
							</div>
						)}
						{audio === "none" && (
							<p className={styles.messageP}>{message}</p>
						)}
					</div>
				</>
			) : (
				<div className={`${styles.assistantMessage} ${styles.message}`}>
					<p className={styles.messageP}>{message}</p>
				</div>
			)}
		</div>
	);
};

export default Message;
