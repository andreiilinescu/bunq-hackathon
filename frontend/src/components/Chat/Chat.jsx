import React, { useEffect } from "react";
import { useState, useRef } from "react";
import MessageBar from "../MessageBar/MessageBar";
import Message from "../Message/Message";
import styles from "./Chat.module.scss";
import { BACKEND_URL, BACKEND_URL_CHAT } from "../../constants";
console.log(BACKEND_URL_CHAT);
import CampaignIcon from "@mui/icons-material/Campaign";
import VolumeOffIcon from "@mui/icons-material/VolumeOff";
const Chat = () => {
	// each message has role (user, assistant) and content (string)
	const [reciteMessages, setReciteMessages] = useState(false);
	const endOfMessagesRef = useRef(null);
	const defaultMessages = [
		{
			role: "assistant",
			content: "Hello! How can I help you today?",
			audio: "none",
		},
		{ role: "user", content: "I need help with my account", audio: "none" },
		{
			role: "assistant",
			content:
				"Sure, I can help with that. What seems to be the problem?",
			audio: "none",
		},
	];
	const [chatHistory, setChatHistory] = useState(defaultMessages);

	const handleSendMessage = async (newMessageContent) => {
		const newMessage = {
			role: "user",
			content: newMessageContent,
			audio: "none",
		};
		//* new user message comes in, add it to chat and make a message for the assistant
		addNewMessage(newMessage);
		//* add a "thinking..." message for the assistant
		const thinkingMessage = {
			role: "assistant",
			content: "Thinking...",
			audio: "none",
		};
		addNewMessage(thinkingMessage);

		const responseMessage = await sendMessageToAPI(newMessageContent);

		// console.log("responseMessage", responseMessage);
		const newAssistantMessage = {
			role: "assistant",
			content: responseMessage,
			audio: "none",
		};
		//* remove the assistant's "thinking..." message and add the new one
		changeLastMessage(newAssistantMessage);
	};
	const addNewMessage = (message) => {
		// Add the new message to the chat history
		setChatHistory((prevHistory) => [...prevHistory, message]);

		// Scroll to the bottom of the chat history
	};
	const scrollToRef = (ref) => {
		if (ref.current) {
			ref.current.scrollIntoView({
				block: "end",
				behavior: "smooth",
			});
		}
	};
	useEffect(() => {
		scrollToRef(endOfMessagesRef);
	}, [chatHistory]); // Scroll to the bottom when chatHistory changes
	const changeLastMessage = (message) => {
		// Change the last message in the chat history
		setChatHistory((prevHistory) => {
			const updatedHistory = [...prevHistory];
			updatedHistory[updatedHistory.length - 1] = message;
			return updatedHistory;
		});
	};
	const reciteAudioFile = async (audioFile) => {
		if (audioFile) {
			try {
				// If it's a URL:
				const audio = new Audio(audioFile);
				// If it's base64 you may need: new Audio(data:audio/mp3;base64,${modelReciteAudioFile});
				await audio.play();
			} catch (err) {
				console.error("Audio playback failed:", err);
			}
		} else {
			// load an audio file from assets
			console.log("playing audio");
			const audio = new Audio("../assets/recording.webm");
			audio.play().catch((error) => {
				console.error("Error playing audio:", error);
			});
		}
	};
	const sendMessageToAPI = async (message) => {
		console.log("Sending message to API:", message);
		const response = await fetch(BACKEND_URL_CHAT, {
			method: "POST",
			headers: {
				"Content-Type": "application/json",
			},
			body: JSON.stringify({
				message: message,
				requestAudio: reciteMessages,
			}),
		});
		const responseData = await response.json();
    
		// Get the text message from the response
		const textMessage = responseData.messages[responseData.messages.length - 1].text;
		
		if (reciteMessages && responseData.audio) {
			// Convert base64 audio to a playable format
			const audioBase64 = responseData.audio;
			const audioBlob = base64ToBlob(audioBase64, 'audio/mp3');
			const audioUrl = URL.createObjectURL(audioBlob);
			await reciteAudioFile(audioUrl);
		}
		
		// Return the text message
		console.log("textMessage", textMessage);
		return textMessage;
		// console.log("Received response from API:", mess);
		// Return the message directly
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
	return (
		<div className={styles.chatContainer}>
			<button
				className={styles.reciteButton}
				onClick={() => setReciteMessages(!reciteMessages)}
			>
				{reciteMessages ? <CampaignIcon /> : <VolumeOffIcon />}
			</button>
			<div className={styles.chatHistory}>
				{chatHistory.map((message, index) => (
					<Message
						key={index}
						message={message.content}
						role={message.role}
						audio={message.audio}
					/>
				))}
				<div ref={endOfMessagesRef} />
			</div>
			<div className={styles.messageBarContainer}>
				<MessageBar
					reciteMessages={reciteMessages}
					functionToPlayAudioAloud={reciteAudioFile}
					onSendMessage={handleSendMessage}
					addNewMessage={addNewMessage}
					changeLastMessage={changeLastMessage}
				/>
			</div>
		</div>
	);
};

export default Chat;
