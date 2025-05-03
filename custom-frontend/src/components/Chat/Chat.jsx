import React from "react";
import { useState } from "react";
import MessageBar from "../MessageBar/MessageBar";
import Message from "../Message/Message";
import styles from "./Chat.module.scss";

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
	const [chatHistory, setChatHistory] = useState(defaultMessages);

	const handleSendMessage = (newMessageContent) => {
		const newMessage = { role: "user", content: newMessageContent };
		//* new user message comes in, add it to chat and make a message for the assistant
		setChatHistory((prevHistory) => [...prevHistory, newMessage]);
		const newAssistantMessage = {
			role: "assistant",
			content: "This is a placeholder response from the assistant.",
		};
		setChatHistory((prevHistory) => [...prevHistory, newAssistantMessage]);
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
			<MessageBar onSendMessage={handleSendMessage} />
		</div>
	);
};

export default Chat;
