import React, { useEffect, useRef, useState } from "react";
import { useWavesurfer } from "@wavesurfer/react";
import RecordPlugin from "wavesurfer.js/dist/plugins/record.esm.js";
import styles from "./Wavesurfer.module.scss";
import CloseIcon from "@mui/icons-material/Close";
import DoneIcon from "@mui/icons-material/Done";
export default function WavesurferComp({ handleStopRecording, onAudioSubmit }) {
	const containerRef = useRef(null);
	const [rec, setRec] = useState(null);

	// Basic waveform renderer
	const { wavesurfer } = useWavesurfer({
		container: containerRef,
		height: 30,
		waveColor: "#0ea5e9",
		progressColor: "#0284c7",
		cursorWidth: 0,
	});

	// Set‑up Record plugin and auto‑start recording
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

		// Log the final blob when recording stops (checkButton)
		record.on("record-end", (blob) => {
			console.log("Recording finished:", blob);
		});

		// Auto‑start as soon as a mic is available
		(async () => {
			const [{ deviceId } = {}] =
				await RecordPlugin.getAvailableAudioDevices();
			await record.startRecording({ deviceId });
		})();

		return () => record.destroy();
	}, [wavesurfer]);

	const submit = async () => {
		if (!rec) return;
		if (rec.isRecording()) {
			const blob = await rec.stopRecording();
			// console.log("✅ Prompt would be sent with this blob:", blob);
			onAudioSubmit(blob);
		}
	};

	return (
		<div className={styles.container}>
			<div className={styles.btnContainer}>
				<button
					className={`${styles.sendButton}  ${styles.btn} `}
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
			<div ref={containerRef} className={styles.waveform} />
		</div>
	);
}
