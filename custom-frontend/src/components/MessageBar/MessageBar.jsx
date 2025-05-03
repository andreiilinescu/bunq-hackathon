import React from "react";
import styles from "./MessageBar.module.scss";
import MicNoneIcon from "@mui/icons-material/MicNone";
import SettingsVoiceIcon from "@mui/icons-material/SettingsVoice";
import SendIcon from "@mui/icons-material/Send";
import WaveSurferComp from "../VoiceViz/WavesurferComp";
import { useState } from "react";

const MessageBar = ({ onSendMessage }) => {
	const [message, setMessage] = useState("");
	const [isRecording, setIsRecording] = useState(false); // State to track recording status
	const handleInputChange = (event) => {
		setMessage(event.target.value);
	};

	const handleSubmit = () => {
		if (message.trim()) {
			onSendMessage(message); // Call the function passed from the parent component
		}
	};

	const handleKeyDown = (event) => {
		if (event.key === "Enter") {
			handleSubmit();
		}
	};
	const handleMicClick = () => {
		// Handle microphone click event here
		console.log("Microphone clicked!");
		setIsRecording(!isRecording); // Toggle recording state
	};
	const handleStopRecording = () => {
		setIsRecording(false); // Stop recording
	};
	return (
		<div className={styles.container}>
			<div>
				{isRecording && (
					<WaveSurferComp handleStopRecording={handleStopRecording} />
				)}
				{!isRecording && (
					<div
						className={styles.voiceIconContainer}
						onClick={handleMicClick}
					>
						<MicNoneIcon />
					</div>
				)}
			</div>

			<input
				type="text"
				placeholder="Write a message..."
				className={styles.inputField}
				value={message}
				onChange={handleInputChange}
				onKeyDown={handleKeyDown} // Add key down handler
			/>
			<button className={styles.sendButton} onClick={handleSubmit}>
				<div className={styles.sendIconContainer}>
					<SendIcon />
				</div>
			</button>
		</div>
	);
};

export default MessageBar;
