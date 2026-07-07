import { useEffect, useState, useRef } from 'react';
import { useParams, Link } from 'react-router-dom';
import { ArrowLeft, Send, ShieldAlert, Phone, Building2, User, Link2 } from 'lucide-react';
import { getSessionDetail, sendSessionMessage } from '../../lib/api';
import PageTransition from '../../components/PageTransition';

export default function SessionDetail() {
  const { id } = useParams<{ id: string }>();
  const [session, setSession] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [message, setMessage] = useState('');
  const [sending, setSending] = useState(false);
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (id) {
      getSessionDetail(id).then(data => {
        setSession(data);
        setLoading(false);
      }).catch(err => {
        console.error(err);
        setLoading(false);
      });
    }
  }, [id]);

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [session?.messages]);

  const handleSendMessage = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!message.trim() || !id || sending) return;

    setSending(true);
    const userMsg = message;
    setMessage('');

    // Optimistic UI update
    const tempUserMsg = { id: Date.now(), role: 'user', content: userMsg, created_at: new Date().toISOString() };
    setSession((prev: any) => ({
      ...prev,
      messages: [...prev.messages, tempUserMsg]
    }));

    try {
      const aiMsg = await sendSessionMessage(id, userMsg);
      setSession((prev: any) => ({
        ...prev,
        messages: [...prev.messages, aiMsg]
      }));
    } catch (error) {
      console.error(error);
      // Remove optimistic message on failure
      setSession((prev: any) => ({
        ...prev,
        messages: prev.messages.filter((m: any) => m.id !== tempUserMsg.id)
      }));
    } finally {
      setSending(false);
    }
  };

  const getEntityIcon = (type: string) => {
    switch (type) {
      case 'phone': return <Phone className="w-3 h-3" />;
      case 'bank_account': return <Building2 className="w-3 h-3" />;
      case 'upi_id': return <Link2 className="w-3 h-3" />;
      case 'name': return <User className="w-3 h-3" />;
      default: return null;
    }
  };

  if (loading) {
    return (
      <div className="flex justify-center items-center h-screen">
        <div className="w-8 h-8 border-2 border-electric-blue border-t-transparent rounded-full animate-spin"></div>
      </div>
    );
  }

  if (!session) {
    return (
      <div className="text-center py-20">
        <h2 className="text-2xl font-bold text-slate-300">Session not found</h2>
        <Link to="/dashboard" className="text-electric-blue hover:underline mt-4 inline-block">Return to Dashboard</Link>
      </div>
    );
  }

  return (
    <PageTransition>
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 h-[calc(100vh-80px)] flex flex-col">
        {/* Header */}
        <div className="flex items-center gap-4 mb-6 shrink-0">
          <Link to="/dashboard" className="p-2 hover:bg-white/5 rounded-lg transition-colors text-slate-400 hover:text-white">
            <ArrowLeft className="w-5 h-5" />
          </Link>
          <div>
            <div className="flex items-center gap-3">
              <h1 className="text-2xl font-bold font-mono">REP-{session.id.split('-')[0].toUpperCase()}</h1>
              {session.status === 'pending' ? (
                <span className="px-2 py-1 rounded text-xs font-bold bg-slate-500/20 text-slate-400">
                  Pending Audio
                </span>
              ) : (
                <span className={`px-2 py-1 rounded text-xs font-bold ${
                  session.risk_score >= 70 ? 'bg-alert-red/20 text-alert-red' : 
                  session.risk_score >= 40 ? 'bg-yellow-500/20 text-yellow-500' : 
                  'bg-safe-green/20 text-safe-green'
                }`}>
                  {session.risk_score}/100 Risk
                </span>
              )}
            </div>
            <p className="text-slate-400 text-sm mt-1">Submitted on {new Date(session.created_at).toLocaleString()}</p>
          </div>
        </div>

        {/* Two Column Layout */}
        <div className="flex gap-6 flex-1 min-h-0">
          
          {/* Left Column: Data & Transcript */}
          <div className="w-1/2 flex flex-col gap-6 overflow-y-auto pr-2 custom-scrollbar">
            
            {/* AI Analysis */}
            <div className="glass rounded-xl p-6 border border-white/10">
              <h2 className="text-lg font-bold mb-4 flex items-center gap-2">
                <ShieldAlert className="w-5 h-5 text-electric-blue" />
                AI Analysis
              </h2>
              <p className="text-slate-300 leading-relaxed bg-navy-900/50 p-4 rounded-lg border border-white/5">
                {session.ai_explanation}
              </p>
            </div>

            {/* Extracted Entities */}
            {session.entities && session.entities.length > 0 && (
              <div className="glass rounded-xl p-6 border border-white/10">
                <h2 className="text-lg font-bold mb-4 flex items-center gap-2">
                  <Link2 className="w-5 h-5 text-purple-400" />
                  Extracted Entities
                </h2>
                <div className="flex flex-wrap gap-2">
                  {session.entities.map((e: any) => (
                    <div key={e.id} className="flex items-center gap-1.5 px-3 py-1.5 bg-navy-800 border border-white/10 rounded-lg text-sm text-slate-300">
                      {getEntityIcon(e.type)}
                      <span className="font-mono">{e.value}</span>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Original Transcript */}
            <div className="glass rounded-xl p-6 border border-white/10">
              <h2 className="text-lg font-bold mb-4">Original Transcript</h2>
              <div className="bg-navy-900 p-4 rounded-lg border border-white/5 font-mono text-sm text-slate-400 whitespace-pre-wrap">
                "{session.transcript_text}"
              </div>
            </div>

          </div>

          {/* Right Column: Chat History */}
          <div className="w-1/2 glass rounded-xl border border-white/10 flex flex-col">
            <div className="p-4 border-b border-white/10 bg-navy-900/50">
              <h2 className="font-bold flex items-center gap-2">
                Follow-up Chat History
              </h2>
            </div>
            
            <div ref={scrollRef} className="flex-1 overflow-y-auto p-4 space-y-4 custom-scrollbar bg-navy-950/50">
              {session.messages.length === 0 ? (
                <div className="text-center text-slate-500 mt-10">No follow-up messages yet.</div>
              ) : (
                session.messages.map((msg: any, idx: number) => (
                  <div key={idx} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
                    <div className={`max-w-[85%] rounded-2xl px-4 py-3 ${
                      msg.role === 'user' 
                        ? 'bg-electric-blue text-navy-900 rounded-tr-sm font-medium' 
                        : 'bg-navy-800 border border-white/10 text-slate-200 rounded-tl-sm'
                    }`}>
                      <p className="whitespace-pre-wrap">{msg.content}</p>
                    </div>
                  </div>
                ))
              )}
            </div>

            {/* Chat Input */}
            <div className="p-4 border-t border-white/10 bg-navy-900/50">
              <form onSubmit={handleSendMessage} className="relative flex items-end gap-2">
                <textarea
                  value={message}
                  onChange={(e) => setMessage(e.target.value)}
                  placeholder="Send a message as the officer..."
                  className="w-full bg-navy-950 border border-white/10 rounded-xl pl-4 pr-12 py-3 text-sm focus:outline-none focus:border-electric-blue/50 resize-none"
                  rows={1}
                  onKeyDown={(e) => {
                    if (e.key === 'Enter' && !e.shiftKey) {
                      e.preventDefault();
                      handleSendMessage(e);
                    }
                  }}
                />
                <button 
                  type="submit" 
                  disabled={!message.trim() || sending}
                  className="absolute right-2 bottom-2 p-2 bg-electric-blue text-navy-900 rounded-lg hover:bg-electric-blue-hover disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                >
                  <Send className="w-4 h-4" />
                </button>
              </form>
            </div>
          </div>

        </div>
      </div>
    </PageTransition>
  );
}
