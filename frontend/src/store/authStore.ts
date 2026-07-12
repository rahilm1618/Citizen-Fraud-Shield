import { create } from 'zustand';

interface AuthState {
  token: string | null;
  role: string | null;
  isAuthenticated: boolean;
  login: (token: string) => void;
  logout: () => void;
}

const getRoleFromToken = (token: string | null) => {
  if (!token) return null;
  try {
    const payload = JSON.parse(atob(token.split('.')[1]));
    return payload.role || null;
  } catch (e) {
    return null;
  }
};

const initialToken = localStorage.getItem('token');

export const useAuthStore = create<AuthState>((set) => ({
  token: initialToken,
  role: getRoleFromToken(initialToken),
  isAuthenticated: !!initialToken,
  login: (token: string) => {
    localStorage.setItem('token', token);
    set({ token, role: getRoleFromToken(token), isAuthenticated: true });
  },
  logout: () => {
    localStorage.removeItem('token');
    set({ token: null, role: null, isAuthenticated: false });
  },
}));
