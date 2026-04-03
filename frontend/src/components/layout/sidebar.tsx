import { Link } from "react-router";

export function Sidebar() {
  return (
    <nav className="w-56 border-r border-border bg-surface-alt p-4">
      <ul className="space-y-2">
        <li>
          <Link to="/" className="block rounded px-3 py-2 text-sm hover:bg-border">
            Orders
          </Link>
        </li>
        <li>
          <Link to="/analytics" className="block rounded px-3 py-2 text-sm hover:bg-border">
            Analytics
          </Link>
        </li>
      </ul>
    </nav>
  );
}
