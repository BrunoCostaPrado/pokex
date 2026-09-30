import { Scan } from "@pokex/ui"
import { tauriCommand } from "../hooks/useTauriQuery"

interface RecognitionResult {
  count: number
  detections: Array<{
    class_id?: string
    detection_confidence: number
    ocr_text?: string
  }>
}

const recognizeCard = (file: File) => tauriCommand<RecognitionResult>("recognize_card", { file })

export function ScanPage() {
  return <Scan recognizeCard={recognizeCard} />
}
