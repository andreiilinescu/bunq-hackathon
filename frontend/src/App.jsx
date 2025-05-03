import React from "react";
import { ChatProvider } from "./custom_components/ChatProvider/ChatProvider";
import Sidebar from "./custom_components/Sidebar/Sidebar";
import ChatWindow from "./custom_components/ChatWindow/ChatWindow";
import "./index.scss";

export default function App() {
	return (
		<ChatProvider>
			<div className="app-grid">
				<Sidebar />
				<ChatWindow />
			</div>
		</ChatProvider>
	);
}
