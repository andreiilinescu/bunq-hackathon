import { useState } from "react";
import reactLogo from "./assets/react.svg";
import viteLogo from "/vite.svg";
import styles from "./App.module.scss";
import Chat from "./components/Chat/Chat";
function App() {
	const [count, setCount] = useState(0);

	return (
		<div className={styles.mainContainer}>
			<div className={styles.mainCol}>
				<Chat />
			</div>
		</div>
	);
}

export default App;
