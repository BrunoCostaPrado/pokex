import { Scan } from "@pokex/ui"

async function recognizeCard(file: File) {
  const form = new FormData()
  form.append("file", file)
  const res = await fetch("/recognition/api/v1/recognize", {
    method: "POST",
    body: form,
  })
  if (!res.ok) throw new Error("Recognition failed")
  return res.json()
}

export default function ScanPage() {
  return <Scan recognizeCard={recognizeCard} />
}
