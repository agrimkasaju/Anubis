import React, { useState } from 'react';
import { KeyRound, X, Check, Shield } from 'lucide-react';
import { getStoredToken, setStoredToken } from '../utils/auth';

interface AuthModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSuccess: () => void;
}

export const AuthModal: React.FC<AuthModalProps> = ({ isOpen, onClose, onSuccess }) => {
  const [tokenInput, setTokenInput] = useState(getStoredToken());

  if (!isOpen) return null;

  const handleSave = () => {
    setStoredToken(tokenInput.trim());
    onSuccess();
    onClose();
  };

  const handleClear = () => {
    setStoredToken('');
    setTokenInput('');
    onSuccess();
  };

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-md animate-fade-in"
      onClick={onClose}
    >
      <div
        className="nexus-glass rounded-2xl w-full max-w-md p-5 border border-cyan-500/40 space-y-4 shadow-2xl"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center justify-between border-b border-sky-900/40 pb-3">
          <div className="flex items-center space-x-2">
            <Shield className="w-4 h-4 text-cyan-400" />
            <h3 className="font-mono text-sm font-bold text-white uppercase tracking-wider">
              Orion Access Token
            </h3>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="p-1 rounded-lg bg-slate-900 hover:bg-slate-800 text-slate-400 hover:text-slate-200"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        <p className="text-xs font-mono text-slate-400 leading-relaxed">
          Enter the secure dashboard token configured in <code className="text-cyan-300">config/api_keys.json</code>. The token is stored locally in session storage and never transmitted to third parties.
        </p>

        <div className="space-y-1">
          <label className="text-[10px] font-mono uppercase tracking-wider text-slate-400">
            Security Token
          </label>
          <div className="relative">
            <KeyRound className="w-4 h-4 text-slate-500 absolute left-3 top-1/2 -translate-y-1/2" />
            <input
              type="password"
              value={tokenInput}
              onChange={(e) => setTokenInput(e.target.value)}
              placeholder="Paste 16-hex token..."
              className="w-full pl-9 pr-3.5 py-2.5 bg-slate-950 border border-sky-900/40 rounded-xl text-xs font-mono text-slate-100 placeholder-slate-600 focus:outline-none focus:border-cyan-500"
            />
          </div>
        </div>

        <div className="flex items-center space-x-2 pt-2">
          <button
            type="button"
            onClick={handleSave}
            className="flex-1 flex items-center justify-center space-x-1.5 py-2.5 bg-cyan-600 hover:bg-cyan-500 active:scale-95 text-slate-950 font-mono font-bold text-xs rounded-xl transition shadow-lg shadow-cyan-950/40"
          >
            <Check className="w-3.5 h-3.5" />
            <span>AUTHENTICATE</span>
          </button>
          <button
            type="button"
            onClick={handleClear}
            className="px-3 py-2.5 bg-slate-900 hover:bg-rose-950/40 text-slate-400 hover:text-rose-300 font-mono text-xs rounded-xl border border-slate-800 transition"
          >
            CLEAR
          </button>
        </div>
      </div>
    </div>
  );
};
