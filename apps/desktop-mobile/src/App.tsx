import { Link, Route, Switch, useLocation } from "wouter"
import { CardDetailPage } from "./pages/CardDetail"
import { CollectionPage } from "./pages/Collection"
import { ScanPage } from "./pages/Scan"
import { SetDetailPage } from "./pages/SetDetail"
import { SetsListPage } from "./pages/SetsList"
import { Settings } from "./pages/Settings"

const navItems = [
  { to: "/", label: "Sets" },
  { to: "/scan", label: "Scan" },
  { to: "/collection", label: "Collection" },
  { to: "/settings", label: "Settings" },
]

function Layout() {
  const [location] = useLocation()
  return (
    <div className="min-h-screen bg-[var(--color-background)]">
      <header className="bg-white border-b border-[var(--color-border)] px-4 py-3">
        <div className="max-w-6xl mx-auto flex items-center justify-between">
          <Link href="/" className="text-lg font-bold text-[var(--color-text)]">
            PokéX
          </Link>
          <nav className="flex gap-4">
            {navItems.map(item => (
              <Link
                key={item.to}
                href={item.to}
                className={`text-sm font-medium transition-colors ${
                  location === item.to || (item.to !== "/" && location.startsWith(item.to))
                    ? "text-[var(--color-primary)]"
                    : "text-[var(--color-text-muted)] hover:text-[var(--color-text)]"
                }`}
              >
                {item.label}
              </Link>
            ))}
          </nav>
        </div>
      </header>
      <main className="max-w-6xl mx-auto p-4">
        <Switch>
          <Route path="/" component={SetsListPage} />
          <Route path="/sets/:id" component={SetDetailPage} />
          <Route path="/cards/:id" component={CardDetailPage} />
          <Route path="/scan" component={ScanPage} />
          <Route path="/collection" component={CollectionPage} />
          <Route path="/settings" component={Settings} />
        </Switch>
      </main>
    </div>
  )
}

export default function App() {
  return <Layout />
}
