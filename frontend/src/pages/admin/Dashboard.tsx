import { useEffect, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { Network, Search, X, Phone, Building2, User, Link2, ShieldAlert } from 'lucide-react';
import { getAdminSessions } from '../../lib/api';
import PageTransition from '../../components/PageTransition';

export default function Dashboard() {
  const [sessions, setSessions] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  
  // Search & Filter state
  const [searchQuery, setSearchQuery] = useState('');
  const [filterRisk, setFilterRisk] = useState<string>('all');
  
  // Quick View Modal state
  const [quickViewSession, setQuickViewSession] = useState<any | null>(null);

  const navigate = useNavigate();

  const fetchSessions = async () => {
    try {
      const data = await getAdminSessions();
      setSessions(data);
    } catch (err) {
      console.error(err);
    }
  };

  useEffect(() => {
    fetchSessions().then(() => setLoading(false));

    // Polling every 5 seconds for new reports
    const intervalId = setInterval(() => {
      fetchSessions();
    }, 5000);

    return () => clearInterval(intervalId);
  }, []);

  const getEntityIcon = (type: string) => {
    switch (type) {
      case 'phone': return <Phone className="w-3 h-3" />;
      case 'bank_account': return <Building2 className="w-3 h-3" />;
      case 'upi_id': return <Link2 className="w-3 h-3" />;
      case 'name': return <User className="w-3 h-3" />;
      default: return null;
    }
  };

  const filteredSessions = sessions.filter(s => {
    // Filter by risk
    if (filterRisk === 'high' && s.risk_score < 70) return false;
    if (filterRisk === 'medium' && (s.risk_score < 40 || s.risk_score >= 70)) return false;
    if (filterRisk === 'low' && s.risk_score >= 40) return false;
    
    // Filter by search query (id or explanation snippet)
    if (searchQuery) {
      const q = searchQuery.toLowerCase();
      if (!s.id.toLowerCase().includes(q) && !s.ai_explanation?.toLowerCase().includes(q)) {
        return false;
      }
    }
    
    return true;
  });

  return (
    <PageTransition>
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 relative">
        <div className="flex justify-between items-center mb-8">
          <div>
            <h1 className="text-3xl font-bold">Fraud Reports</h1>
            <p className="text-slate-400 mt-1">Review flagged digital arrest and scam sessions.</p>
          </div>
          <Link 
            to="/dashboard/graph" 
            className="flex items-center gap-2 px-4 py-2 bg-purple-500/20 text-purple-400 border border-purple-500/30 rounded-lg hover:bg-purple-500/30 transition-colors"
          >
            <Network className="w-5 h-5" />
            View Network Graph
          </Link>
        </div>

        <div className="glass rounded-2xl overflow-hidden border-t border-white/20 relative z-10">
          <div className="p-4 border-b border-white/10 flex gap-4">
            <div className="relative flex-1">
              <Search className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
              <input 
                type="text" 
                placeholder="Search reports by ID or explanation..." 
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="w-full bg-navy-800 border border-white/10 rounded-lg pl-10 pr-4 py-2 text-sm focus:outline-none focus:ring-1 focus:ring-electric-blue"
              />
            </div>
            <select 
              value={filterRisk}
              onChange={(e) => setFilterRisk(e.target.value)}
              className="flex items-center gap-2 px-4 py-2 bg-navy-800 border border-white/10 rounded-lg text-sm text-slate-300 hover:text-white transition-colors focus:outline-none focus:ring-1 focus:ring-electric-blue appearance-none"
            >
              <option value="all">All Risks</option>
              <option value="high">High Risk (70+)</option>
              <option value="medium">Medium Risk (40-69)</option>
              <option value="low">Low Risk (&lt;40)</option>
            </select>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-sm text-left">
              <thead className="text-xs text-slate-400 uppercase bg-navy-900/50">
                <tr>
                  <th className="px-6 py-4">ID / Date</th>
                  <th className="px-6 py-4">Risk Score</th>
                  <th className="px-6 py-4">Explanation Snippet</th>
                  <th className="px-6 py-4 text-right">Actions</th>
                </tr>
              </thead>
              <tbody>
                {loading ? (
                  <tr>
                    <td colSpan={4} className="px-6 py-12 text-center text-slate-500">Loading reports...</td>
                  </tr>
                ) : filteredSessions.length === 0 ? (
                  <tr>
                    <td colSpan={4} className="px-6 py-12 text-center text-slate-500">No flagged reports found.</td>
                  </tr>
                ) : (
                  filteredSessions.map((s) => (
                    <tr key={s.id} className="border-b border-white/5 hover:bg-white/5 transition-colors">
                      <td className="px-6 py-4">
                        <div className="font-mono text-xs text-slate-300 mb-1 font-bold">REP-{s.id.split('-')[0].toUpperCase()}</div>
                        <div className="text-xs text-slate-500">{new Date(s.created_at).toLocaleString()}</div>
                      </td>
                      <td className="px-6 py-4">
                        {s.status === 'pending' ? (
                          <span className="inline-flex items-center justify-center px-2 py-1 rounded text-xs font-bold bg-slate-500/20 text-slate-400">
                            Pending Audio
                          </span>
                        ) : (
                          <span className={`inline-flex items-center justify-center px-2 py-1 rounded text-xs font-bold ${
                            s.risk_score >= 70 ? 'bg-alert-red/20 text-alert-red' : 
                            s.risk_score >= 40 ? 'bg-yellow-500/20 text-yellow-500' : 
                            'bg-safe-green/20 text-safe-green'
                          }`}>
                            {s.risk_score}/100
                          </span>
                        )}
                      </td>
                      <td className="px-6 py-4 text-slate-400 max-w-xs truncate">
                        {s.ai_explanation}
                      </td>
                      <td className="px-6 py-4 text-right space-x-3">
                        <button 
                          onClick={() => setQuickViewSession(s)}
                          className="text-slate-300 hover:text-white font-medium text-xs uppercase tracking-wider transition-colors"
                        >
                          Quick View
                        </button>
                        <Link 
                          to={`/dashboard/session/${s.id}`}
                          className="text-electric-blue hover:text-electric-blue-hover font-medium text-xs uppercase tracking-wider transition-colors"
                        >
                          Full Review
                        </Link>
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </div>

        {/* Quick View Modal Overlay */}
        {quickViewSession && (
          <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-navy-950/80 backdrop-blur-sm transition-all duration-300 animate-in fade-in zoom-in-95">
            <div className="glass w-full max-w-lg rounded-2xl border border-white/10 shadow-2xl overflow-hidden flex flex-col">
              
              <div className="p-4 border-b border-white/10 flex justify-between items-center bg-navy-900/50">
                <div className="flex items-center gap-2">
                  <ShieldAlert className="w-5 h-5 text-electric-blue" />
                  <h3 className="font-bold text-lg">Quick View</h3>
                </div>
                <button 
                  onClick={() => setQuickViewSession(null)}
                  className="p-1 hover:bg-white/10 rounded-lg text-slate-400 hover:text-white transition-colors"
                >
                  <X className="w-5 h-5" />
                </button>
              </div>

              <div className="p-6 space-y-6">
                
                {/* Top Stats */}
                <div className="flex justify-between items-center">
                  <div>
                    <div className="text-xs text-slate-500 uppercase tracking-wider mb-1">Report ID</div>
                    <div className="font-mono text-sm font-bold">REP-{quickViewSession.id.split('-')[0].toUpperCase()}</div>
                  </div>
                  <div className="text-right">
                    <div className="text-xs text-slate-500 uppercase tracking-wider mb-1">Risk Score</div>
                    {quickViewSession.status === 'pending' ? (
                      <span className="inline-flex items-center justify-center px-2 py-1 rounded text-xs font-bold bg-slate-500/20 text-slate-400">
                        Pending
                      </span>
                    ) : (
                      <span className={`inline-flex items-center justify-center px-2 py-1 rounded text-xs font-bold ${
                        quickViewSession.risk_score >= 70 ? 'bg-alert-red/20 text-alert-red' : 
                        quickViewSession.risk_score >= 40 ? 'bg-yellow-500/20 text-yellow-500' : 
                        'bg-safe-green/20 text-safe-green'
                      }`}>
                        {quickViewSession.risk_score}/100
                      </span>
                    )}
                  </div>
                </div>

                {/* Explanation */}
                <div>
                  <div className="text-xs text-slate-500 uppercase tracking-wider mb-2">Top Red Flags (Snippet)</div>
                  <div className="bg-navy-900/50 p-3 rounded-lg border border-white/5 max-h-32 overflow-y-auto custom-scrollbar">
                    <p className="text-sm text-slate-300">
                      {quickViewSession.ai_explanation}
                    </p>
                  </div>
                </div>

                {/* Entities */}
                <div>
                  <div className="text-xs text-slate-500 uppercase tracking-wider mb-2">Linked Entities</div>
                  {quickViewSession.entities && quickViewSession.entities.length > 0 ? (
                    <div className="flex flex-wrap gap-2">
                      {quickViewSession.entities.map((e: any) => (
                        <div key={e.id} className="flex items-center gap-1.5 px-2.5 py-1 bg-navy-800 border border-white/10 rounded-md text-xs text-slate-300">
                          {getEntityIcon(e.type)}
                          <span className="font-mono">{e.value}</span>
                        </div>
                      ))}
                    </div>
                  ) : (
                    <div className="text-sm text-slate-500">No entities extracted.</div>
                  )}
                </div>

              </div>

              <div className="p-4 border-t border-white/10 bg-navy-900/50 flex justify-end">
                <button 
                  onClick={() => navigate(`/dashboard/session/${quickViewSession.id}`)}
                  className="px-4 py-2 bg-electric-blue text-navy-900 font-bold rounded-lg hover:bg-electric-blue-hover transition-colors flex items-center gap-2 text-sm"
                >
                  Full Review →
                </button>
              </div>

            </div>
          </div>
        )}

      </div>
    </PageTransition>
  );
}
