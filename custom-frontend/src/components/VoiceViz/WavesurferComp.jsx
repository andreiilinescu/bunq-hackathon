import React, { useCallback, useEffect, useRef, useState } from "react";
import { useWavesurfer } from "@wavesurfer/react";
import RecordPlugin from "wavesurfer.js/dist/plugins/record.esm.js";
import styles from "./Wavesurfer.module.scss";

export default function WavesurferComp({ handleStopRecording }) {
	const containerRef = useRef(null);

	// UI state
	const [rec, setRec] = useState(null);
	const [blobUrl, setBlobUrl] = useState(null);
	const [isRecording, setRecFlag] = useState(false);

	// Wavesurfer instance – classic (non‑bars) renderer
	const { wavesurfer, isPlaying, currentTime } = useWavesurfer({
		container: containerRef,
		height: 200,
		waveColor: "#0ea5e9",
		progressColor: "#0284c7",
		cursorWidth: 0,
		barWidth: 0, // line style; bars don’t live‑update
		dragToSeek: false,
	});
	// Attach Record plugin once Wavesurfer is ready
	useEffect(() => {
		if (!wavesurfer) return;

		const record = wavesurfer.registerPlugin(
			RecordPlugin.create({
				continuousWaveform: true,
				mediaRecorderTimeslice: 200, // refresh ~5×/s for live view
				renderRecordedAudio: false,
			})
		);

		record.on("record-start", () => setRecFlag(true));

		record.on("record-end", (blob) => {
			setRecFlag(false);
			const url = URL.createObjectURL(blob);
			setBlobUrl(url);
			wavesurfer.load(url);
		});

		setRec(record);
		return () => record.destroy();
	}, [wavesurfer]);

	useEffect(() => {
		if (!rec) return;
		(async () => {
			const [{ deviceId } = {}] =
				await RecordPlugin.getAvailableAudioDevices();
			await rec.startRecording({ deviceId }); // ⬅️ auto‑start
		})();
	}, [rec]);
	// handlers
	const toggleRec = useCallback(async () => {
		if (!rec) return;

		if (rec.isRecording()) {
			rec.stopRecording();
		} else {
			const [{ deviceId } = {}] =
				await RecordPlugin.getAvailableAudioDevices();
			await rec.startRecording({ deviceId });
		}
	}, [rec]);

	const togglePlay = useCallback(() => {
		if (!wavesurfer) return;

		// If the cursor is at (or very near) the end, jump back to 0 s
		const endThreshold = 0.05; // seconds
		if (
			wavesurfer.getDuration() &&
			wavesurfer.getCurrentTime() >=
				wavesurfer.getDuration() - endThreshold
		) {
			wavesurfer.seekTo(0);
		}

		wavesurfer.playPause();
	}, [wavesurfer]);

	const downloadRecording = () => {
		if (!blobUrl) return;
		const a = document.createElement("a");
		a.href = blobUrl;
		a.download = "recording.webm";
		a.click();
	};

	return (
		<div className={styles.container}>
			<div ref={containerRef} className={styles.waveform} />

			<div className={styles.btnRow}>
				<button className={styles.btn} onClick={toggleRec}>
					{isRecording ? "Stop" : "Record"}
				</button>

				<button
					className={styles.btn}
					onClick={togglePlay}
					disabled={!blobUrl}
				>
					{isPlaying ? "Pause" : "Play"}
				</button>

				<button
					className={styles.btn}
					onClick={downloadRecording}
					disabled={!blobUrl}
				>
					Download
				</button>
			</div>

			{blobUrl && (
				<span className={styles.timer}>{currentTime.toFixed(1)} s</span>
			)}
			<button
				className={styles.escButton}
				onClick={handleStopRecording}
			></button>
		</div>
	);
}
