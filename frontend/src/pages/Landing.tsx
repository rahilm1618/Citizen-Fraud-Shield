import { motion } from 'framer-motion';
import { Link } from 'react-router-dom';
import { ShieldAlert, Activity, Network } from 'lucide-react';
import PageTransition from '../components/PageTransition';

export default function Landing() {
  return (
    <PageTransition>
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 pt-10">
        
        {/* Hero */}
        <div className="text-center py-20 lg:py-32">
          <motion.div
            initial={{ scale: 0.8, opacity: 0 }}
            animate={{ scale: 1, opacity: 1 }}
            transition={{ type: 'spring', duration: 1 }}
            className="inline-flex items-center gap-2 px-4 py-2 rounded-full glass text-sm font-medium text-electric-blue mb-8 border-electric-blue/30"
          >
            <span className="relative flex h-2 w-2">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-electric-blue opacity-75"></span>
              <span className="relative inline-flex rounded-full h-2 w-2 bg-electric-blue"></span>
            </span>
            Real-time Scam Protection
          </motion.div>
          
          <h1 className="text-5xl md:text-7xl font-extrabold tracking-tight mb-8 drop-shadow-sm">
            Stop <span className="text-transparent bg-clip-text bg-linear-to-r from-alert-red to-orange-500">Digital Arrests</span> <br className="hidden md:block"/> Before They Happen.
          </h1>
          
          <p className="mt-4 text-xl text-slate-400 max-w-3xl mx-auto mb-10 leading-relaxed">
            Paste a suspicious message or call transcript. Our AI instantly analyzes it against known fraud patterns, while quietly mapping the scammer's network for law enforcement.
          </p>
          
          <div className="flex justify-center gap-4">
            <Link to="/check" className="px-8 py-4 bg-electric-blue hover:bg-electric-blue-hover text-white rounded-xl font-bold transition-all shadow-[0_0_20px_rgba(59,130,246,0.4)] hover:shadow-[0_0_30px_rgba(59,130,246,0.6)] hover:-translate-y-1 flex items-center gap-2">
              <ShieldAlert className="w-5 h-5" />
              Check a Message Now
            </Link>
          </div>
        </div>

        {/* Features */}
        <div className="grid md:grid-cols-3 gap-8 py-20">
          <div className="glass p-8 rounded-3xl hover:bg-navy-800/80 transition-colors">
            <div className="w-12 h-12 rounded-xl bg-blue-500/10 flex items-center justify-center mb-6">
              <Activity className="w-6 h-6 text-electric-blue" />
            </div>
            <h3 className="text-xl font-bold mb-3">Instant AI Analysis</h3>
            <p className="text-slate-400 leading-relaxed">Advanced language models score your transcript against a live database of Indian scam scripts within seconds.</p>
          </div>
          
          <div className="glass p-8 rounded-3xl hover:bg-navy-800/80 transition-colors">
            <div className="w-12 h-12 rounded-xl bg-green-500/10 flex items-center justify-center mb-6">
              <ShieldAlert className="w-6 h-6 text-safe-green" />
            </div>
            <h3 className="text-xl font-bold mb-3">Plain-English Verdicts</h3>
            <p className="text-slate-400 leading-relaxed">No confusing technical jargon. Get clear, actionable advice on exactly what to do next to protect yourself.</p>
          </div>

          <div className="glass p-8 rounded-3xl hover:bg-navy-800/80 transition-colors">
            <div className="w-12 h-12 rounded-xl bg-purple-500/10 flex items-center justify-center mb-6">
              <Network className="w-6 h-6 text-purple-400" />
            </div>
            <h3 className="text-xl font-bold mb-3">Hidden Graph Linking</h3>
            <p className="text-slate-400 leading-relaxed">Behind the scenes, we extract bank accounts and phone numbers to build a network graph for law enforcement.</p>
          </div>
        </div>
      </div>
    </PageTransition>
  );
}
