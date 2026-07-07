import { motion } from 'framer-motion';

export default function TypingIndicator() {
  return (
    <div className="flex gap-1 p-4 bg-navy-800 rounded-2xl rounded-tl-sm w-16">
      {[0, 1, 2].map((i) => (
        <motion.div
          key={i}
          className="w-2 h-2 bg-white/50 rounded-full"
          animate={{ y: [0, -5, 0] }}
          transition={{ duration: 0.6, repeat: Infinity, delay: i * 0.2 }}
        />
      ))}
    </div>
  );
}
