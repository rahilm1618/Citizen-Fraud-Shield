import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import { AnimatePresence } from 'framer-motion';

import Navbar from './components/Navbar';
import Landing from './pages/Landing';
import Check from './pages/Check';
import Login from './pages/Login';
import Dashboard from './pages/admin/Dashboard';
import GraphView from './pages/admin/GraphView';
import SessionDetail from './pages/admin/SessionDetail';
import ProtectedRoute from './components/ProtectedRoute';
import CustomCursor from './components/CustomCursor';

function App() {
  return (
    <Router>
      <CustomCursor />
      <div className="min-h-screen text-foreground selection:bg-electric-blue/30 selection:text-white flex flex-col relative overflow-hidden cursor-none">
        {/* Background glow effects */}
        <div className="absolute top-[-20%] left-[-10%] w-[50%] h-[50%] bg-electric-blue/10 rounded-full blur-[120px] pointer-events-none" />
        <div className="absolute bottom-[-20%] right-[-10%] w-[50%] h-[50%] bg-purple-500/10 rounded-full blur-[120px] pointer-events-none" />
        
        <Navbar />
        
        <main className="flex-1 relative z-10">
          <AnimatePresence mode="wait">
            <Routes>
              <Route path="/" element={<Landing />} />
              <Route path="/check" element={<Check />} />
              <Route path="/login" element={<Login />} />
              
              <Route element={<ProtectedRoute />}>
                <Route path="/dashboard" element={<Dashboard />} />
                <Route path="/dashboard/session/:id" element={<SessionDetail />} />
                <Route path="/dashboard/graph" element={<GraphView />} />
              </Route>
            </Routes>
          </AnimatePresence>
        </main>
      </div>
    </Router>
  );
}

export default App;
