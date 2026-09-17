import { motion } from 'motion/react';

interface TranscriptionFeedProps {
  text: string;
}

export const TranscriptionFeed = ({ text }: TranscriptionFeedProps) => {
  if (!text) return null;

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -10 }}
      className="flex-1 overflow-y-auto pr-2"
    >
      <p className="text-white/90 text-sm leading-relaxed font-medium whitespace-pre-wrap break-words">
        {text}
      </p>
    </motion.div>
  );
};