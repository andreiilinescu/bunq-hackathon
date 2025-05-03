import React, { useRef, useState, useEffect, useCallback } from "react";
import { useWavesurfer } from "@wavesurfer/react";
import PlayArrowIcon from "@mui/icons-material/PlayArrow";
import PauseIcon from "@mui/icons-material/Pause";
import styles from "./AudioPlayer.module.scss"; // Assuming you will create this SCSS file

const AudioPlayer = ({ audioBlob }) => {
	const containerRef = useRef(null);
	const [isPlaying, setIsPlaying] = useState(false);
	const [audioUrl, setAudioUrl] = useState(null);

	// Create a URL from the blob when the component mounts or blob changes
	useEffect(() => {
		if (audioBlob) {
			const url = URL.createObjectURL(audioBlob);
			setAudioUrl(url);
			// Clean up the object URL when the component unmounts or blob changes
			return () => URL.revokeObjectURL(url);
		}
	}, [audioBlob]);

	const { wavesurfer, isReady } = useWavesurfer({
		container: containerRef,
		url: audioUrl, // Use the blob URL
		waveColor: "#A1A1AA", // Gray color for the wave
		progressColor: "#0ea5e9", // Accent color for progress
		cursorWidth: 0, // Hide the cursor
		height: 30, // Adjust height as needed
		barWidth: 2, // Optional: Adjust bar width
		barGap: 1, // Optional: Adjust gap between bars
	});

	const onPlayPause = useCallback(() => {
		if (wavesurfer) {
			wavesurfer.playPause();
		}
	}, [wavesurfer]);

	// Update isPlaying state based on wavesurfer events
	useEffect(() => {
		if (!wavesurfer) return;

		const subscriptions = [
			wavesurfer.on("play", () => setIsPlaying(true)),
			wavesurfer.on("pause", () => setIsPlaying(false)),
			wavesurfer.on("finish", () => setIsPlaying(false)), // Reset on finish
		];

		return () => {
			subscriptions.forEach((unsub) => unsub());
		};
	}, [wavesurfer]);

	if (!audioBlob) {
		return null; // Don't render if no blob is provided
	}

	return (
		<div className={styles.audioPlayerContainer}>
			<button
				onClick={onPlayPause}
				disabled={!isReady}
				className={styles.playButton}
			>
				{isPlaying ? <PauseIcon /> : <PlayArrowIcon />}
			</button>
			<div ref={containerRef} className={styles.waveform} />
		</div>
	);
};

export default AudioPlayer;
