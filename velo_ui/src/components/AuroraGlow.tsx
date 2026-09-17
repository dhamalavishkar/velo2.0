import { motion } from 'motion/react';

export const AuroraGlow = ({ color }: { color: string }) => {
  const hex = color.replace('bg-[', '').replace(']', '') || color;
  return (
    <div className="absolute inset-x-0 bottom-0 h-1/2 overflow-hidden rounded-b-[40px] pointer-events-none opacity-60">
      <motion.div
        className="absolute -bottom-6 w-[120%] -left-[10%] h-16"
        style={{
          background: `radial-gradient(ellipse at center, ${hex} 0%, transparent 70%)`,
          willChange: 'transform, opacity',
        }}
        animate={{
          x: ['-4%', '4%', '-4%'],
          y: ['0%', '15%', '0%'],
          scale: [1, 1.1, 1],
          opacity: [0.5, 0.8, 0.5],
        }}
        transition={{
          duration: 4,
          repeat: Infinity,
          ease: 'easeInOut',
        }}
      />
    </div>
  );
};