import { useMutation, useQueryClient } from "@tanstack/react-query"
import { useState } from "react"

interface Detection {
  class_id?: string
  detection_confidence: number
  ocr_text?: string
}

interface RecognitionResult {
  count: number
  detections: Detection[]
}

interface ScanProps {
  recognizeCard: (file: File) => Promise<RecognitionResult>
}

export function Scan({ recognizeCard }: ScanProps) {
  const [preview, setPreview] = useState<string | null>(null)
  const queryClient = useQueryClient()
  const { mutate, data, isPending } = useMutation({
    mutationFn: recognizeCard,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["recognitions"] }),
  })

  const handleFile = (file: File) => {
    const reader = new FileReader()
    reader.onload = e => setPreview(e.target?.result as string)
    reader.readAsDataURL(file)
    mutate(file)
  }

  return (
    <div>
      <h1 className="text-2xl font-bold mb-6">Scan a Card</h1>
      <div className="border-2 border-dashed border-[var(--color-border)] rounded-lg p-8 text-center">
        <input
          type="file"
          accept="image/*"
          capture="environment"
          onChange={e => e.target.files?.[0] && handleFile(e.target.files[0])}
          className="hidden"
          id="scan-input"
        />
        <label htmlFor="scan-input" className="cursor-pointer">
          <div className="text-4xl mb-2">📸</div>
          <p className="text-[var(--color-text-muted)]">Click to upload or take photo</p>
        </label>
      </div>
      {preview && <img src={preview} alt="Preview" className="mt-4 max-h-64 mx-auto rounded-lg" />}
      {isPending && <p className="text-center py-4 text-[var(--color-text-muted)]">Analyzing...</p>}
      {data && (
        <div className="mt-4">
          <h2 className="font-bold mb-2">Results ({data.count} detected)</h2>
          {data.detections.map((d: Detection) => {
            const stableKey = d.class_id ?? `${d.detection_confidence}-${d.ocr_text ?? "none"}`
            return (
              <div
                key={stableKey}
                className="bg-white border border-[var(--color-border)] rounded-lg p-3 mb-2"
              >
                <p className="text-sm">Confidence: {(d.detection_confidence * 100).toFixed(1)}%</p>
                {d.ocr_text && (
                  <p className="text-sm text-[var(--color-text-muted)]">OCR: {d.ocr_text}</p>
                )}
              </div>
            )
          })}
        </div>
      )}
    </div>
  )
}
