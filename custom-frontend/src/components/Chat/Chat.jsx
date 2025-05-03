import React from "react";
import { useState } from "react";
import MessageBar from "../MessageBar/MessageBar";
import Message from "../Message/Message";
import styles from "./Chat.module.scss";
const baseURL = import.meta.env.VITE_LOCALHOST_URL;
console.log(baseURL);
const chatURL = `${baseURL}/chat`;
const Chat = () => {
	// each message has role (user, assistant) and content (string)
	const defaultMessages = [
		{ role: "assistant", content: "Hello! How can I help you today?" },
		{ role: "user", content: "I need help with my account" },
		{
			role: "assistant",
			content:
				"Sure, I can help with that. What seems to be the problem?",
		},
	];
	const audioMessageSubmit = async (resonse) => {};
	const [chatHistory, setChatHistory] = useState(defaultMessages);

	const handleSendMessage = async (newMessageContent) => {
		const newMessage = { role: "user", content: newMessageContent };
		//* new user message comes in, add it to chat and make a message for the assistant
		addNewMessage(newMessage);
		//* add a "thinking..." message for the assistant
		const thinkingMessage = {
			role: "assistant",
			content: "Thinking...",
		};
		addNewMessage(thinkingMessage);

		const responseMessage = await sendMessageToAPI(newMessageContent);

		// console.log("responseMessage", responseMessage);
		const newAssistantMessage = {
			role: "assistant",
			content: responseMessage,
		};
		//* remove the assistant's "thinking..." message and add the new one
		changeLastMessage(newAssistantMessage);
	};
	const addNewMessage = (message) => {
		// Add the new message to the chat history
		setChatHistory((prevHistory) => [...prevHistory, message]);
	};
	const changeLastMessage = (message) => {
		// Change the last message in the chat history
		setChatHistory((prevHistory) => {
			const updatedHistory = [...prevHistory];
			updatedHistory[updatedHistory.length - 1] = message;
			return updatedHistory;
		});
	};
	const sendMessageToAPI = async (message) => {
		console.log("Sending message to API:", message);
		const response = await fetch(chatURL, {
			method: "POST",
			headers: {
				"Content-Type": "application/json",
			},
			body: JSON.stringify({ message: message }),
		});
		const data = await response.json();
		const mess = data.messages[0].text;
		// console.log("Received response from API:", mess);
		// Return the message directly
		return mess;
	};
	return (
		<div className={styles.chatContainer}>
			<div className={styles.chatHistory}>
				{chatHistory.map((message, index) => (
					<Message
						key={index}
						message={message.content}
						role={message.role}
					/>
				))}
			</div>
			<div className={styles.messageBarContainer}>
				<MessageBar
					onSendMessage={handleSendMessage}
					addNewMessage={addNewMessage}
					changeLastMessage={changeLastMessage}
				/>
			</div>
		</div>
	);
};

export default Chat;
