import { useState, useRef, useEffect } from 'react';
import PageTransition from '../components/PageTransition';
import MessageBubble from '../components/MessageBubble';
import TypingIndicator from '../components/TypingIndicator';
import RiskScoreCard from '../components/RiskScoreCard';
import { Send, Mic, Square } from 'lucide-react';
import { createSession, sendFollowupMessage } from '../lib/api';
import type { SessionResponse } from '../lib/types';
import { useAudioCapture } from '../hooks/useAudioCapture';
import { motion, AnimatePresence } from 'framer-motion';

export default function Check() {
  const [input, setInput] = useState('');
  const [messages, setMessages] = useState<{role: string, content: string}[]>([]);
  const [isTyping, setIsTyping] = useState(false);
  const [session, setSession] = useState<SessionResponse | null>(null);
  const scrollRef = useRef<HTMLDivElement>(null);

  const handleScoreUpdate = (updatedSession: SessionResponse) => {
    setSession(updatedSession);
    if (updatedSession.transcript_text) {
      setMessages([
        { role: 'user', content: updatedSession.transcript_text },
        { role: 'assistant', content: updatedSession.ai_explanation || 'Analyzing...' }
      ]);
    }
  };

  const { isRecording, error: audioError, startRecording, stopRecording } = useAudioCapture(handleScoreUpdate);

  useEffect(() => {
    if (isRecording) {
      setMessages([]);
      setInput('');
    }
  }, [isRecording]);

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages, isTyping]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim()) return;

    const userText = input.trim();
    setInput('');
    setMessages(prev => [...prev, { role: 'user', content: userText }]);
    setIsTyping(true);

    try {
      if (!session) {
        // First message: Create session
        const res = await createSession(userText);
        setSession(res);
        setMessages(prev => [...prev, { role: 'assistant', content: res.ai_explanation }]);
      } else {
        // Follow up
        const res = await sendFollowupMessage(session.id, userText);
        setMessages(prev => [...prev, { role: 'assistant', content: res.content }]);
      }
    } catch (error) {
      setMessages(prev => [...prev, { role: 'assistant', content: "Sorry, I couldn't process that request right now. Please try again later." }]);
    } finally {
      setIsTyping(false);
    }
  };

  return (
    <PageTransition>
      <div className="max-w-6xl mx-auto px-4 py-8 grid grid-cols-1 lg:grid-cols-3 gap-8 min-h-[calc(100vh-80px)] lg:h-[calc(100vh-80px)]">
        
        {/* Chat Window */}
        <div className="lg:col-span-2 glass rounded-3xl flex flex-col overflow-hidden shadow-2xl relative border-t border-white/20">
          
          <div className="bg-navy-900/80 backdrop-blur-md p-4 border-b border-white/10 shrink-0">
            <h2 className="font-bold flex items-center gap-2">
              <div className="w-2 h-2 rounded-full bg-safe-green animate-pulse" />
              Live AI Analysis
            </h2>
            <p className="text-xs text-slate-400 mt-1">Paste your transcript or describe the suspicious call below.</p>
          </div>

          <div ref={scrollRef} className="flex-1 overflow-y-auto p-6 space-y-6 scroll-smooth">
            {messages.length === 0 && (
              <div className="h-full flex flex-col items-center justify-center text-slate-500 text-center">
                <p className="mb-2">No messages yet.</p>
                <p className="text-sm max-w-sm">Type or paste what the caller said to you, use Live Listen, and we'll analyze it immediately.</p>
                {audioError && <p className="text-sm text-alert-red mt-4">{audioError}</p>}
              </div>
            )}
            
            {messages.map((msg, i) => (
              <MessageBubble key={i} message={msg} />
            ))}
            
            {isRecording && (
              <div className="mt-6 flex flex-col items-center pb-4">
                <div className="w-16 h-16 rounded-full bg-alert-red/20 flex items-center justify-center animate-pulse mb-3">
                  <Mic className="w-8 h-8 text-alert-red" />
                </div>
                <p className="text-sm font-bold text-alert-red">Listening to conversation...</p>
              </div>
            )}
            
            {isTyping && (
              <motion.div initial={{opacity:0}} animate={{opacity:1}}>
                <TypingIndicator />
              </motion.div>
            )}
          </div>

          <form onSubmit={handleSubmit} className="p-4 bg-navy-900/50 border-t border-white/10 shrink-0">
            <div className="flex justify-between items-center mb-3">
              <span className="text-xs text-slate-400">
                🎙️ For live detection, use this on a separate device or browser tab from the one on the call — your phone's microphone is likely in use by the call itself.
              </span>
            </div>
            <div className="relative flex items-center gap-2">
              {isRecording ? (
                <button
                  type="button"
                  onClick={stopRecording}
                  className="p-3.5 bg-alert-red/20 text-alert-red border border-alert-red/50 rounded-xl hover:bg-alert-red/30 transition-colors flex items-center gap-2 whitespace-nowrap"
                >
                  <Square className="w-5 h-5 fill-current" />
                  <span className="text-sm font-bold hidden sm:inline">Stop</span>
                </button>
              ) : (
                <button
                  type="button"
                  onClick={startRecording}
                  disabled={isTyping}
                  className="p-3.5 bg-navy-800 text-electric-blue border border-white/10 rounded-xl hover:bg-white/5 transition-colors flex items-center gap-2 whitespace-nowrap"
                  title="Live Listen"
                >
                  <Mic className="w-5 h-5" />
                  <span className="text-sm font-bold hidden sm:inline">Live Listen</span>
                </button>
              )}
              <div className="relative flex-1 flex items-center">
                <input
                  type="text"
                  value={input}
                  onChange={e => setInput(e.target.value)}
                  placeholder="Type your message or paste a transcript..."
                  className="w-full bg-navy-800 border border-white/10 rounded-xl py-4 pl-4 pr-12 focus:outline-none focus:ring-2 focus:ring-electric-blue/50 text-sm transition-all"
                  disabled={isTyping || isRecording}
                />
                <button 
                  type="submit" 
                  disabled={!input.trim() || isTyping || isRecording}
                  className="absolute right-2 p-2 bg-electric-blue text-white rounded-lg hover:bg-electric-blue-hover disabled:opacity-50 disabled:hover:bg-electric-blue transition-colors"
                >
                  <Send className="w-4 h-4" />
                </button>
              </div>
            </div>
          </form>
        </div>

        {/* Info Panel */}
        <div className="space-y-6">
          <AnimatePresence>
            {session && (
              session.status === 'pending' ? (
                <motion.div 
                  initial={{ scale: 0.9, opacity: 0 }}
                  animate={{ scale: 1, opacity: 1 }}
                  className="glass p-6 rounded-2xl flex flex-col items-center justify-center border-t border-white/20"
                >
                  <h3 className="text-sm text-slate-400 font-medium mb-2 uppercase tracking-wider">AI Risk Verdict</h3>
                  <div className="text-2xl font-black text-slate-400 drop-shadow-md py-4">
                    Listening...
                  </div>
                  <p className="mt-3 text-sm text-slate-300 text-center max-w-50">
                    Awaiting audio to analyze risk score.
                  </p>
                </motion.div>
              ) : (
                <RiskScoreCard score={session.risk_score} />
              )
            )}
          </AnimatePresence>

          <div className="glass p-6 rounded-2xl">
            <h3 className="font-bold text-lg mb-4 text-slate-200">How it works</h3>
            <ul className="space-y-4 text-sm text-slate-400">
              <li className="flex gap-3 items-start">
                <div className="w-6 h-6 rounded bg-electric-blue/20 text-electric-blue flex items-center justify-center shrink-0 mt-0.5">1</div>
                <p>Paste the exact message or describe the phone call.</p>
              </li>
              <li className="flex gap-3 items-start">
                <div className="w-6 h-6 rounded bg-electric-blue/20 text-electric-blue flex items-center justify-center shrink-0 mt-0.5">2</div>
                <p>Our AI scores the text against a live database of Indian scam scripts.</p>
              </li>
              <li className="flex gap-3 items-start">
                <div className="w-6 h-6 rounded bg-electric-blue/20 text-electric-blue flex items-center justify-center shrink-0 mt-0.5">3</div>
                <p>You get an instant verdict and advice on what to do next.</p>
              </li>
            </ul>
          </div>
        </div>

      </div>
    </PageTransition>
  );
}
