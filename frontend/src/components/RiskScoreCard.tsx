import { motion } from 'framer-motion';
import { useEffect, useState } from 'react';

export default function RiskScoreCard({ score }: { score: number }) {
  const [displayScore, setDisplayScore] = useState(0);
  
  useEffect(() => {
    let start = 0;
    const duration = 1500;
    const interval = 16;
    const step = (score / duration) * interval;
    
    const timer = setInterval(() => {
      start += step;
      if (start > score) {
        setDisplayScore(score);
        clearInterval(timer);
      } else {
        setDisplayScore(Math.floor(start));
      }
    }, interval);
    
    return () => clearInterval(timer);
  }, [score]);

  const getColor = () => {
    if (score < 40) return 'text-safe-green';
    if (score < 70) return 'text-yellow-500';
    return 'text-alert-red';
  };

  return (
    <motion.div 
      initial={{ scale: 0.9, opacity: 0 }}
      animate={{ scale: 1, opacity: 1 }}
      className="glass p-6 rounded-2xl flex flex-col items-center justify-center border-t border-white/20"
    >
      <h3 className="text-sm text-slate-400 font-medium mb-2 uppercase tracking-wider">AI Risk Verdict</h3>
      <div className={`text-6xl font-black ${getColor()} drop-shadow-md`}>
        {displayScore}<span className="text-2xl text-slate-500 ml-1">/100</span>
      </div>
      <p className="mt-3 text-sm text-slate-300 text-center max-w-50">
        {score >= 70 ? 'High probability of fraud. Do not proceed.' : 
         score >= 40 ? 'Suspicious pattern detected. Proceed with caution.' : 
         'Low risk detected based on known patterns.'}
      </p>
    </motion.div>
  );
}
