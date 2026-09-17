import { motion } from 'motion/react';
import { Sparkles, Mic } from 'lucide-react';

interface ActivationPopProps {
  phrase: string;
}

export const ActivationPop = ({ phrase }: ActivationPopProps) => {
  return (
    <motion.div
      initial={{ opacity: 0, scale: 0.8, y: 10 }}
      animate={{ opacity: 1, scale: 1, y: 0 }}
      exit={{ opacity: 0, scale: 0.8, y: -10 }}
      className="flex items-center gap-4 w-full"
    >
      <div className="w-12 h-12 rounded-full bg-gradient-to-br from-[#FF0080] to-[#FF6B9D] flex items-center justify-center shadow-lg shadow-[#FF0080]/40 animate-pulse">
        <Sparkles className="w-6 h-6 text-white" />
      </div>
      <div className="flex flex-col text-left">
        <span className="text-white text-sm font-semibold tracking-wide">
          {phrase}
        </span>
        <span className="text-white/60 text-xs font-medium">
          Activating VELO...
        </span>
      </div>
      <motion.div
        className="absolute right-4 w-6 h-6 rounded-full bg-gradient-to-br from-[#FF0080] to-[#FF6B9D] flex items-center justify-center"
        animate={{ scale: [1, 1.2, 1], rotate: [0, 180, 360] }}
        transition={{ duration: 1.5, repeat: Infinity, ease: 'easeInOut' }}
      >
        <Mic className="w-3.5 h-3.5 text-white" />
      </motion.div>
    </motion.div>
  );
};