import React from "react";
import styles from "./MessageBar.module.scss";
import MicNoneIcon from "@mui/icons-material/MicNone";
import SettingsVoiceIcon from "@mui/icons-material/SettingsVoice";
import SendIcon from "@mui/icons-material/Send";
import WaveSurferComp from "../VoiceViz/WavesurferComp";
import { useState } from "react";

const baseURL = import.meta.env.VITE_LOCALHOST_URL;
const MessageBar = ({ onSendMessage, addNewMessage, changeLastMessage }) => {
	const [message, setMessage] = useState("");
	const [isRecording, setIsRecording] = useState(false); // State to track recording status
	const handleInputChange = (event) => {
		setMessage(event.target.value);
	};
	const handleAudioSubmit = async (blob) => {
		// dowloadRecording(blob);
		handleStopRecording();
		const fullURL = `${baseURL}/voice`;
		await sendRecordingToAPI(blob); // Send the recording to the API
	};
	const dowloadRecording = (blob) => {
		// Handle sending the recorded audio blob here
		const url = URL.createObjectURL(blob);
		const a = document.createElement("a");
		a.href = url;
		a.download = "recording.webm";
		a.click();
	};
	const clearMessageBarText = () => {
		setMessage(""); // Clear the message input field
	};
	/**
	 * Send the recorded audio to your backend.
	 * @param {Blob} blob - Audio captured by WaveSurfer’s Record plugin
	 */
	const sendRecordingToAPI = async (blob) => {
		addNewMessage({
			role: "user",
			content: "Audio message",
		});
		const formData = new FormData();
		formData.append("audio", blob, "recording.webm");
		const response = await fetch(`${baseURL}/voice`, {
			method: "POST",
			body: formData,
		});
		if (!response.ok) {
			console.error("Error sending audio to API:", response.statusText);
		} else {
			console.log("Audio sent successfully!");
		}
		const data = await response.json();
		const modelMessage = data.messages[0].text;
		addNewMessage({
			role: "assistant",
			content: modelMessage,
		});
	};

	const handleSubmit = () => {
		if (message.trim()) {
			onSendMessage(message); // Call the function passed from the parent component
			clearMessageBarText(); // Clear the message input field after sending
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
		<div
			className={`${styles.container} ${
				isRecording ? styles.recording : ""
			}`}
		>
			<div>
				{isRecording && (
					<div className={styles.waveformContainer}>
						<WaveSurferComp
							handleStopRecording={handleStopRecording}
							onAudioSubmit={handleAudioSubmit}
						/>
					</div>
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
			{!isRecording && (
				<input
					type="text"
					placeholder="Write a message..."
					className={styles.inputField}
					value={message}
					onChange={handleInputChange}
					onKeyDown={handleKeyDown} // Add key down handler
				/>
			)}
			{!isRecording && (
				<button className={styles.sendButton} onClick={handleSubmit}>
					<div className={styles.sendIconContainer}>
						<SendIcon />
					</div>
				</button>
			)}
		</div>
	);
};

export default MessageBar;
