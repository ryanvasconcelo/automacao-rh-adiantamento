// frontend/src/components/Login.jsx
import React, { useState } from 'react';
import { User, Lock, ArrowRight, AlertTriangle, Eye, EyeOff } from 'lucide-react';
import { motion } from 'framer-motion';
import logoProjecont from '../assets/logoProjecont.jpeg';
import { SmartButton } from './ui/Shared';

const VALID_USERS = {
    'admin': 'admin!@#',
    'isabela.caetano': '$Audit@88IC',
    'joel.goncalves': 'JGAudit#Rhol8!9',
    'gisele.felix': 'GF@Fin$77%$'
};

export default function Login({ onLogin }) {
    const [username, setUsername] = useState('');
    const [password, setPassword] = useState('');
    const [showPassword, setShowPassword] = useState(false);
    const [rememberMe, setRememberMe] = useState(false);
    const [error, setError] = useState('');
    const [loading, setLoading] = useState(false);

    const handleSubmit = (e) => {
        e?.preventDefault();
        setLoading(true);
        setError('');

        setTimeout(() => {
            if (VALID_USERS[username] && VALID_USERS[username] === password) {
                const token = btoa(username + ':' + Date.now());
                const storage = rememberMe ? localStorage : sessionStorage;
                storage.setItem('user_token', token);
                onLogin(username);
            } else {
                setError('Usuário ou senha incorretos.');
                setLoading(false);
            }
        }, 800);
    };

    return (
        <div className="min-h-screen flex items-center justify-center p-4 bg-slate-900 relative overflow-hidden">
            {/* Background Effects */}
            <div className="absolute inset-0 bg-gradient-to-br from-indigo-900/40 via-slate-900 to-slate-950 z-0"></div>
            <div className="absolute top-[-20%] left-[-10%] w-[500px] h-[500px] bg-indigo-600/20 rounded-full blur-[120px] z-0"></div>
            <div className="absolute bottom-[-20%] right-[-10%] w-[500px] h-[500px] bg-purple-600/20 rounded-full blur-[120px] z-0"></div>

            <motion.div
                initial={{ opacity: 0, scale: 0.95, y: 20 }}
                animate={{ opacity: 1, scale: 1, y: 0 }}
                transition={{ duration: 0.4 }}
                className="w-full max-w-md bg-white/95 backdrop-blur-xl rounded-3xl shadow-2xl shadow-black/50 overflow-hidden border border-white/10 z-10"
            >
                {/* Header with Logo */}
                <div className="bg-gradient-to-br from-slate-50 to-slate-100 p-8 text-center border-b border-slate-100/50">
                    <motion.img
                        initial={{ y: -20, opacity: 0 }}
                        animate={{ y: 0, opacity: 1 }}
                        transition={{ delay: 0.2 }}
                        src={logoProjecont}
                        alt="Projecont"
                        className="w-24 h-24 mx-auto mb-4 rounded-2xl shadow-lg shadow-indigo-500/20 object-cover ring-4 ring-white"
                    />
                    <h1 className="text-2xl font-bold text-slate-800 tracking-tight">GFS Auditoria</h1>
                    <p className="text-xs font-semibold text-slate-400 uppercase tracking-widest mt-1">Projecont DP Tools</p>
                </div>

                <div className="p-8 space-y-6">
                    <form onSubmit={handleSubmit} className="space-y-5">
                        <div className="space-y-2">
                            <label className="text-xs font-bold text-slate-500 uppercase ml-1">Usuário</label>
                            <div className="relative group">
                                <div className="absolute left-3 top-3 text-slate-400 group-focus-within:text-indigo-600 transition-colors">
                                    <User size={18} />
                                </div>
                                <input
                                    type="text"
                                    value={username}
                                    onChange={e => setUsername(e.target.value)}
                                    className="w-full pl-10 pr-4 py-3 bg-slate-50 border border-slate-200 rounded-xl text-sm font-medium focus:ring-2 focus:ring-indigo-500 focus:border-transparent outline-none transition-all placeholder:text-slate-300"
                                    placeholder="Digite seu usuário..."
                                />
                            </div>
                        </div>

                        <div className="space-y-2">
                            <label className="text-xs font-bold text-slate-500 uppercase ml-1">Senha de Acesso</label>
                            <div className="relative group">
                                <div className="absolute left-3 top-3 text-slate-400 group-focus-within:text-indigo-600 transition-colors">
                                    <Lock size={18} />
                                </div>
                                <input
                                    type={showPassword ? "text" : "password"}
                                    value={password}
                                    onChange={e => setPassword(e.target.value)}
                                    className="w-full pl-10 pr-10 py-3 bg-slate-50 border border-slate-200 rounded-xl text-sm font-medium focus:ring-2 focus:ring-indigo-500 focus:border-transparent outline-none transition-all placeholder:text-slate-300 font-mono"
                                    placeholder="••••••••"
                                />
                                <button
                                    type="button"
                                    onClick={() => setShowPassword(!showPassword)}
                                    className="absolute right-3 top-3 text-slate-400 hover:text-slate-600 transition-colors"
                                >
                                    {showPassword ? <EyeOff size={18} /> : <Eye size={18} />}
                                </button>
                            </div>
                        </div>

                        <div className="flex items-center pt-2">
                            <label className="flex items-center cursor-pointer group">
                                <div className="relative">
                                    <input
                                        type="checkbox"
                                        checked={rememberMe}
                                        onChange={e => setRememberMe(e.target.checked)}
                                        className="sr-only"
                                    />
                                    <div className={`w-10 h-6 bg-slate-200 rounded-full shadow-inner transition-colors ${rememberMe ? 'bg-green-600' : 'bg-slate-500'}`}></div>
                                    <div className={`absolute top-1 left-1 w-4 h-4 bg-white rounded-full shadow transition-transform ${rememberMe ? 'translate-x-4' : ''}`}></div>
                                </div>
                                <span className={`ml-3 text-sm font-medium transition-colors ${rememberMe ? 'text-green-500' : 'text-slate-500'}`}>Lembrar de mim</span>
                            </label>
                        </div>

                        {error && (
                            <motion.div
                                initial={{ opacity: 0, height: 0 }}
                                animate={{ opacity: 1, height: 'auto' }}
                                className="p-3 bg-rose-50 border border-rose-100 rounded-lg flex items-center gap-3 text-rose-600 text-sm font-medium"
                            >
                                <AlertTriangle size={16} /> {error}
                            </motion.div>
                        )}

                        <SmartButton
                            type="submit"
                            isLoading={loading}
                            icon={ArrowRight}
                            variant="primary"
                            className="w-full bg-gradient-to-r from-indigo-600 to-purple-600 hover:from-indigo-700 hover:to-purple-700 shadow-lg shadow-indigo-500/30 border-none py-4"
                        >
                            <span className="text-white font-bold tracking-wide">ACESSAR SISTEMA</span>
                        </SmartButton>
                    </form>
                </div>

                <div className="bg-slate-50 p-4 text-center border-t border-slate-100">
                    <p className="text-[10px] text-slate-400 font-medium">
                        &copy; 2026 Projecont &bull; GFS Auditoria &bull; v1.4.0
                    </p>
                </div>
            </motion.div>
        </div>
    );
}
