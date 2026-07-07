import { Link } from 'react-router-dom';
import { ShieldCheck } from 'lucide-react';
import { useAuthStore } from '../store/authStore';

export default function Navbar() {
  const isAuthenticated = useAuthStore((state) => state.isAuthenticated);
  const logout = useAuthStore((state) => state.logout);

  return (
    <nav className="fixed top-0 w-full z-50 glass border-b border-white/5">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-16">
          <Link to="/" className="flex items-center gap-2">
            <ShieldCheck className="w-8 h-8 text-electric-blue" />
            <span className="font-bold text-xl tracking-tight">Citizen Fraud Shield</span>
          </Link>
          <div className="flex gap-4 items-center">
            <Link to="/check" className="text-sm font-medium hover:text-electric-blue transition-colors flex items-center">
              Check Scan
            </Link>
            
            {isAuthenticated ? (
              <>
                <Link to="/dashboard" className="text-sm font-medium text-slate-300 hover:text-white transition-colors">
                  Dashboard
                </Link>
                <button onClick={logout} className="text-sm font-medium text-alert-red hover:text-red-400 transition-colors">
                  Logout
                </button>
              </>
            ) : (
              <Link to="/login" className="text-sm font-medium text-slate-400 hover:text-white transition-colors">
                Officer Login
              </Link>
            )}
          </div>
        </div>
      </div>
    </nav>
  );
}
