import { useState } from "react"

interface LoadingStateProps {
  message?: string
}

export function LoadingState({ message = "Loading..." }: LoadingStateProps) {
  return (
    <div className="text-center py-8 text-[var(--color-text-muted)]">
      {message}
    </div>
  )
}