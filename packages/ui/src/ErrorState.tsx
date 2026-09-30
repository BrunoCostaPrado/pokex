interface ErrorStateProps {
  message?: string
}

export function ErrorState({ message = "Failed to load" }: ErrorStateProps) {
  return <div className="text-center py-8 text-[var(--color-error)]">{message}</div>
}
