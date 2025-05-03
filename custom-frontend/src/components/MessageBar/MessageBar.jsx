import React from "react";
import styles from "./MessageBar.module.scss";
import MicNoneIcon from "@mui/icons-material/MicNone";
import SettingsVoiceIcon from "@mui/icons-material/SettingsVoice";
import SendIcon from "@mui/icons-material/Send";
import WaveSurferComp from "../VoiceViz/WavesurferComp";
import { useState, useRef, useEffect } from "react";
import { BACKEND_URL, BACKEND_URL_VOICE } from "../../constants";
console.log(BACKEND_URL_VOICE);
const MessageBar = ({
	reciteMessages,
	functionToPlayAudioAloud,
	onSendMessage,
	addNewMessage,
	changeLastMessage,
}) => {
	const [message, setMessage] = useState("");
	const [isRecording, setIsRecording] = useState(false); // State to track recording status
	const [containerWidthRem, setContainerWidthRem] = useState(0);
	const containerRef = useRef(null);
	useEffect(() => {
		const updateWidth = () => {
			if (!containerRef.current) return;
			const px = containerRef.current.clientWidth;
			const rootFontSize = parseFloat(
				getComputedStyle(document.documentElement).fontSize
			);
			setContainerWidthRem(px / rootFontSize);
		};

		updateWidth();
		window.addEventListener("resize", updateWidth);
		return () => window.removeEventListener("resize", updateWidth);
	}, []);

	const handleInputChange = (event) => {
		setMessage(event.target.value);
	};
	const handleAudioSubmit = async (blob) => {
		// dowloadRecording(blob);
		handleStopRecording();
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
			content: "Audio messagsse",
			audio: blob,
		});
		addNewMessage({
			role: "assistant",
			content: "Thinking...",
			audio: "hone",
		});
		// console.log()
		const formData = new FormData();
		formData.append("audio", blob, "recording.webm");
		formData.append("requestAudio", reciteMessages);
		const response = await fetch(BACKEND_URL_VOICE, {
			method: "POST",
			body: formData,
		});
		if (!response.ok) {
			console.error("Error sending audio to API:", response.statusText);
		} else {
			console.log("Audio sent successfully!");
		}

		const responseData = await response.json();
    
		// Get the text message from the response
		const textMessage = responseData.messages[responseData.messages.length - 1].text;
		
		if (reciteMessages && responseData.audio) {
			// Convert base64 audio to a playable format
			const audioBase64 = responseData.audio;
			const audioBlob = base64ToBlob(audioBase64, 'audio/mp3');
			const audioUrl = URL.createObjectURL(audioBlob);
			await functionToPlayAudioAloud(audioUrl);
		}

		changeLastMessage({
			role: "assistant",
			content: textMessage,
			audio: "none",
		});
	};
	const base64ToBlob = (base64, mimeType) => {
		const byteCharacters = atob(base64);
		const byteArrays = [];
		
		for (let i = 0; i < byteCharacters.length; i += 512) {
			const slice = byteCharacters.slice(i, i + 512);
			const byteNumbers = new Array(slice.length);
			
			for (let j = 0; j < slice.length; j++) {
				byteNumbers[j] = slice.charCodeAt(j);
			}
			
			const byteArray = new Uint8Array(byteNumbers);
			byteArrays.push(byteArray);
		}
		
		return new Blob(byteArrays, { type: mimeType });
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
			ref={containerRef}
			className={`${styles.container} ${
				isRecording ? styles.recording : ""
			}`}
		>
			<div>
				{isRecording && (
					<div className={styles.waveformContainer}>
						<WaveSurferComp
							widthRem={containerWidthRem}
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
