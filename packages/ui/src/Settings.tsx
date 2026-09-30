import { useState } from "react"

interface SettingsSectionProps {
  title: string
  children: React.ReactNode
}

export function SettingsSection({ title, children }: SettingsSectionProps) {
  return (
    <div className="mb-8">
      <h2 className="text-lg font-semibold mb-4">{title}</h2>
      <div className="bg-white rounded-lg border border-[var(--color-border)] p-4">{children}</div>
    </div>
  )
}

interface ToggleProps {
  label: string
  description?: string
  checked: boolean
  onChange: (checked: boolean) => void
}

export function Toggle({ label, description, checked, onChange }: ToggleProps) {
  return (
    <label className="flex items-center justify-between py-3 cursor-pointer">
      <div>
        <p className="font-medium">{label}</p>
        {description && <p className="text-sm text-[var(--color-text-muted)]">{description}</p>}
      </div>
      <input
        type="checkbox"
        checked={checked}
        onChange={e => onChange(e.target.checked)}
        className="w-5 h-5 text-[var(--color-primary)] border-[var(--color-border)] rounded focus:ring-[var(--color-primary)]"
      />
    </label>
  )
}

interface SelectProps {
  label: string
  value: string
  options: Array<{ value: string; label: string }>
  onChange: (value: string) => void
}

export function Select({ label, value, options, onChange }: SelectProps) {
  const selectId = `select-${label.toLowerCase().replace(/\s+/g, "-")}`
  return (
    <div className="py-3">
      <label htmlFor={selectId} className="block text-sm font-medium mb-1">
        {label}
      </label>
      <select
        id={selectId}
        value={value}
        onChange={e => onChange(e.target.value)}
        className="w-full px-3 py-2 border border-[var(--color-border)] rounded-lg focus:outline-none focus:ring-2 focus:ring-[var(--color-primary)]"
      >
        {options.map(opt => (
          <option key={opt.value} value={opt.value}>
            {opt.label}
          </option>
        ))}
      </select>
    </div>
  )
}

export function Settings() {
  const [darkMode, setDarkMode] = useState(false)
  const [notifications, setNotifications] = useState(true)
  const [language, setLanguage] = useState("en")
  const [autoSync, setAutoSync] = useState(true)

  return (
    <div className="max-w-2xl">
      <h1 className="text-2xl font-bold mb-6">Settings</h1>

      <SettingsSection title="Appearance">
        <Toggle
          label="Dark Mode"
          description="Use dark theme throughout the app"
          checked={darkMode}
          onChange={setDarkMode}
        />
        <Select
          label="Language"
          value={language}
          options={[
            { value: "en", label: "English" },
            { value: "es", label: "Español" },
            { value: "fr", label: "Français" },
            { value: "de", label: "Deutsch" },
            { value: "ja", label: "日本語" },
          ]}
          onChange={setLanguage}
        />
      </SettingsSection>

      <SettingsSection title="Data & Sync">
        <Toggle
          label="Auto Sync"
          description="Automatically sync collection data in background"
          checked={autoSync}
          onChange={setAutoSync}
        />
        <Toggle
          label="Notifications"
          description="Receive push notifications for price alerts"
          checked={notifications}
          onChange={setNotifications}
        />
      </SettingsSection>

      <SettingsSection title="About">
        <div className="text-sm text-[var(--color-text-muted)]">
          <p>PokéX v0.1.0</p>
          <p className="mt-1">Pokémon TCG Collection Manager</p>
        </div>
      </SettingsSection>
    </div>
  )
}
