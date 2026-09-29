import { BrowserRouter, Link, Outlet, Route, Routes, useLocation } from "react-router-dom"
import CardDetail from "./pages/CardDetail"
import Collection from "./pages/Collection"
import Scan from "./pages/Scan"
import SetDetail from "./pages/SetDetail"
import SetsList from "./pages/SetsList"

const navItems = [
  { to: "/", label: "Sets" },
  { to: "/scan", label: "Scan" },
  { to: "/collection", label: "Collection" },
]

function Layout() {
  const location = useLocation()
  return (
    <div className="min-h-screen bg-[var(--color-background)]">
      <header className="bg-white border-b border-[var(--color-border)] px-4 py-3">
        <div className="max-w-6xl mx-auto flex items-center justify-between">
          <Link to="/" className="text-lg font-bold text-[var(--color-text)]">
            PokéX
          </Link>
          <nav className="flex gap-4">
            {navItems.map(item => (
              <Link
                key={item.to}
                to={item.to}
                className={`text-sm font-medium transition-colors ${
                  location.pathname === item.to ||
                  (item.to !== "/" && location.pathname.startsWith(item.to))
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
        <Outlet />
      </main>
    </div>
  )
}

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route element={<Layout />}>
          <Route index element={<SetsList />} />
          <Route path="sets/:id" element={<SetDetail />} />
          <Route path="cards/:id" element={<CardDetail />} />
          <Route path="scan" element={<Scan />} />
          <Route path="collection" element={<Collection />} />
        </Route>
      </Routes>
    </BrowserRouter>
  )
}
