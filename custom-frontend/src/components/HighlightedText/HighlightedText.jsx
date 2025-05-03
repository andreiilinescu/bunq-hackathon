import React from "react";
import styles from "./HighlightedText.module.scss";

const HighlightedText = ({ text }) => {
	const highlightWord = "bunq";
	// Split text by 'bunq' (case-insensitive)
	const regex = new RegExp(`(${highlightWord})`, "gi");
	const parts = text.split(regex);

	return (
		<>
			{parts.map((part, index) =>
				part.toLowerCase() === highlightWord ? (
					<span key={index} className={styles.highlight}>
						{part}
					</span>
				) : (
					<React.Fragment key={index}>{part}</React.Fragment>
				)
			)}
		</>
	);
};
export default HighlightedText;
