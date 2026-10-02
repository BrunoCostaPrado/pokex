import { Scan } from "@pokex/ui"
import { invoke } from "@tauri-apps/api/core"

interface RecognitionResult {
  count: number
  detections: Array<{
    class_id?: string
    detection_confidence: number
    ocr_text?: string
  }>
}

const recognizeCard = (file: File) => invoke<RecognitionResult>("recognize_card", { file })

export function ScanPage() {
  return <Scan recognizeCard={recognizeCard} />
}
