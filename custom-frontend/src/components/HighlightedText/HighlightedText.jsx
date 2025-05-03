import React from "react";
import styles from "./HighlightedText.module.scss";
import ReactMarkdown from 'react-markdown';
import rehypeRaw from 'rehype-raw';

const HighlightedText = ({ text, highlightWord }) => {
  // First convert markdown to HTML with highlighted words
  if (highlightWord) {
    const regex = new RegExp(`(${highlightWord})`, "gi");
    text = text.replace(regex, `<span class="${styles.highlight}">$1</span>`);
  }
  
  // Then render markdown with the HTML already inserted
  return <ReactMarkdown rehypePlugins={[rehypeRaw]}>{text}</ReactMarkdown>;
};

export default HighlightedText;