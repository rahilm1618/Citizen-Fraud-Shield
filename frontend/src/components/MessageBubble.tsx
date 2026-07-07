import { motion } from 'framer-motion';
import type { MessageResponse } from '../lib/types';
import clsx from 'clsx';
import { ShieldAlert, User } from 'lucide-react';

export default function MessageBubble({ message }: { message: MessageResponse | {role: string, content: string} }) {
  const isAi = message.role === 'assistant';
  
  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      className={clsx(
        "flex w-full gap-3",
        isAi ? "justify-start" : "justify-end"
      )}
    >
      {isAi && (
        <div className="w-8 h-8 rounded-full bg-electric-blue/20 flex items-center justify-center shrink-0">
          <ShieldAlert className="w-4 h-4 text-electric-blue" />
        </div>
      )}
      
      <div className={clsx(
        "max-w-[80%] p-4 rounded-2xl text-sm leading-relaxed",
        isAi ? "bg-navy-800 rounded-tl-sm border border-white/5" : "bg-electric-blue text-white rounded-tr-sm shadow-md"
      )}>
        {message.content}
      </div>

      {!isAi && (
        <div className="w-8 h-8 rounded-full bg-slate-700 flex items-center justify-center shrink-0">
          <User className="w-4 h-4 text-slate-300" />
        </div>
      )}
    </motion.div>
  );
}
