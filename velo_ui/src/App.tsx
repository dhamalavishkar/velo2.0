import React, { useState, useRef, useEffect } from 'react';
import { NotchProvider } from './context/NotchContext';
import { Notch } from './components';
import { useWebSocket, useTextInput } from './hooks/useWebSocket';
import { useNotchController } from './hooks/useNotchController';
import './index.css';

// Inner app — must be inside NotchProvider to access context
function VeloInner() {
  useNotchController();
  const { send, connected } = useWebSocket();
  const { submit } = useTextInput(send);
  const [inputText, setInputText] = useState('');
  const [showInput, setShowInput] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  // Ctrl+Space to toggle text input overlay (testing / accessibility mode)
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.ctrlKey && e.code === 'Space') {
        setShowInput((v) => !v);
        setTimeout(() => inputRef.current?.focus(), 100);
      }
      if (e.key === 'Escape') setShowInput(false);
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, []);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (submit(inputText)) {
      setInputText('');
      setShowInput(false);
    }
  };

  return (
    <div
      className="w-full h-screen bg-transparent overflow-hidden relative"
      style={{ backgroundColor: 'transparent' }}
    >
      {/* Drag region */}
      <div
        className="absolute top-0 w-full h-8 pointer-events-none z-40"
        style={{ WebkitAppRegion: 'drag' } as React.CSSProperties}
      />

      {/* Connection indicator (dev only) */}
      <div
        className={`absolute top-1 right-2 w-2 h-2 rounded-full z-50 transition-colors ${
          connected ? 'bg-green-500' : 'bg-red-500'
        }`}
        title={connected ? 'Connected to VELO backend' : 'Disconnected'}
      />

      {/* Main Notch UI */}
      <Notch />

      {/* Text input overlay (Ctrl+Space) */}
      {showInput && (
        <div className="absolute top-20 left-1/2 -translate-x-1/2 z-50 w-96">
          <form
            onSubmit={handleSubmit}
            className="flex gap-2 bg-black/80 backdrop-blur-xl border border-white/20 rounded-2xl p-3 shadow-2xl"
          >
            <input
              ref={inputRef}
              type="text"
              value={inputText}
              onChange={(e) => setInputText(e.target.value)}
              placeholder="Type a command... (Esc to close)"
              className="flex-1 bg-transparent text-white text-sm placeholder-white/40 outline-none"
              autoFocus
            />
            <button
              type="submit"
              disabled={!inputText.trim() || !connected}
              className="text-xs px-3 py-1.5 rounded-xl bg-purple-600 hover:bg-purple-500 disabled:opacity-40 text-white font-medium transition-colors"
            >
              Send
            </button>
          </form>
          <p className="text-center text-white/30 text-xs mt-1">Ctrl+Space to toggle • Esc to close</p>
        </div>
      )}
    </div>
  );
}

function App() {
  return (
    <NotchProvider>
      <VeloInner />
    </NotchProvider>
  );
}

export default App;