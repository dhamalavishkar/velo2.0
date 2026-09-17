import { motion, useMotionValue, useSpring, useTransform } from 'motion/react';
import { useEffect, useRef } from 'react';

export const Waveform = () => {
  const barsRef = useRef<HTMLDivElement[]>([]);
  const values = Array.from({ length: 16 }, () => useMotionValue(0.1));
  const springs = values.map(v => useSpring(v, { stiffness: 200, damping: 20 }));

  useEffect(() => {
    const animate = () => {
      values.forEach((v, i) => {
        const baseHeight = 0.15 + Math.random() * 0.7;
        const variation = Math.sin(Date.now() / 100 + i) * 0.15;
        v.set(Math.max(0.1, Math.min(1, baseHeight + variation)));
      });
      requestAnimationFrame(animate);
    };
    animate();
  }, [values]);

  return (
    <div className="flex items-end gap-1 h-8 justify-center">
      {springs.map((spring, i) => (
        <motion.div
          key={i}
          ref={el => { barsRef.current[i] = el!; }}
          className="w-1.5 rounded-full bg-[#2979FF] origin-bottom"
          style={{
            height: useTransform(spring, v => `${v * 100}%`),
            willChange: 'transform',
          }}
        />
      ))}
    </div>
  );
};