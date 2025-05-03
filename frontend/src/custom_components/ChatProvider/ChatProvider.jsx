import React from "react";
import { AssistantRuntimeProvider } from "@assistant-ui/react";
import { useChatRuntime } from "@assistant-ui/react-ai-sdk";

export const ChatProvider = ({ children }) => {
	// Point the runtime at your own /api/chat handler (could be Express, CF Worker, etc.)
	const runtime = useChatRuntime({ api: "/api/chat" });

	return (
		<AssistantRuntimeProvider runtime={runtime}>
			{children}
		</AssistantRuntimeProvider>
	);
};
