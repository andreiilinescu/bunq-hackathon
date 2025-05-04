import React, { useEffect, useRef, useState } from "react";
import { useWavesurfer } from "@wavesurfer/react";
import RecordPlugin from "wavesurfer.js/dist/plugins/record.esm.js";
import styles from "./Wavesurfer.module.scss";
import CloseIcon from "@mui/icons-material/Close";
import DoneIcon from "@mui/icons-material/Done";

export default function WavesurferComp({
	widthRem,
	handleStopRecording,
	onAudioSubmit,
}) {
	const containerRef = useRef(null);
	const [rec, setRec] = useState(null);

	// Basic waveform renderer (add responsive:true if supported)
	const { wavesurfer } = useWavesurfer({
		container: containerRef,
		height: 30,
		waveColor: "#0ea5e9",
		progressColor: "#0284c7",
		cursorWidth: 0,
		// responsive: true,
		hideScrollbar: true,
		// fillParent: true,
		// responsive: true,   <-- uncomment if your version of Wavesurfer supports this
	});

	// Set-up Record plugin and auto-start recording
	useEffect(() => {
		if (!wavesurfer) return;

		const record = wavesurfer.registerPlugin(
			RecordPlugin.create({
				continuousWaveform: true,
				mediaRecorderTimeslice: 200,
				renderRecordedAudio: false,
			})
		);
		setRec(record);

		record.on("record-end", (blob) => {
			console.log("Recording finished:", blob);
		});

		(async () => {
			const [{ deviceId } = {}] =
				await RecordPlugin.getAvailableAudioDevices();
			await record.startRecording({ deviceId });
		})();

		return () => record.destroy();
	}, [wavesurfer]);

	// Redraw on window resize so Wavesurfer picks up the new width
	useEffect(() => {
		if (!wavesurfer) return;
		const onResize = () => wavesurfer.drawBuffer();
		window.addEventListener("resize", onResize);
		return () => window.removeEventListener("resize", onResize);
	}, [wavesurfer]);

	// Stops the recorder and hands the Blob to the parent
	const submit = () => {
		if (!rec) return;

		const handleRecordEnd = (blob) => {
			onAudioSubmit(blob);
			rec.un("record-end", handleRecordEnd);
		};

		if (typeof rec.once === "function") {
			rec.once("record-end", onAudioSubmit);
		} else {
			rec.on("record-end", handleRecordEnd);
		}

		rec.stopRecording();
	};
	const waveformStyle = {
		"--target_width": `${widthRem - 3}rem`,
	};
	return (
		<div className={styles.container} style={waveformStyle}>
			<div className={styles.btnContainer}>
				<button
					className={`${styles.sendButton}  ${styles.btn}`}
					onClick={submit}
					aria-label="Confirm"
				>
					<DoneIcon />
				</button>

				<button
					className={`${styles.escButton} ${styles.btn}`}
					onClick={handleStopRecording}
					aria-label="Cancel"
				>
					<CloseIcon />
				</button>
			</div>

			{/* This div will now always span 100% of .container’s width */}
			<div ref={containerRef} className={styles.waveform} />
		</div>
	);
}
