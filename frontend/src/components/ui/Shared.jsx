// frontend/src/components/ui/Shared.jsx
import React from 'react';
import { motion } from 'framer-motion';
import { Loader2 } from 'lucide-react';

// --- WRAPPER DE ANIMAÇÃO ---
export const PageTransition = ({ children, className = "" }) => (
    <motion.div
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        exit={{ opacity: 0, y: -10 }}
        transition={{ duration: 0.3, ease: "easeOut" }}
        className={className}
    >
        {children}
    </motion.div>
);

// --- CARD BASE ---
export const Card = ({ children, className = "", noPadding = false }) => (
    <div className={`bg-white rounded-2xl border border-slate-200 shadow-sm hover:shadow-md transition-shadow duration-300 overflow-hidden ${className}`}>
        <div className={noPadding ? "" : "p-6"}>{children}</div>
    </div>
);

// --- BOTÕES ---
export const Button = ({ children, variant = "primary", icon: Icon, isLoading, className = "", ...props }) => {
    const baseStyle = "inline-flex items-center justify-center gap-2 px-5 py-2.5 rounded-xl font-semibold transition-all duration-200 active:scale-95 disabled:opacity-50 disabled:cursor-not-allowed text-sm";

    const variants = {
        primary: "bg-blue-600 hover:bg-blue-700 text-white shadow-blue-200 shadow-lg",
        secondary: "bg-white border border-slate-200 text-slate-700 hover:bg-slate-50 hover:border-slate-300",
        danger: "bg-rose-50 text-rose-600 hover:bg-rose-100 border border-rose-100",
        ghost: "bg-transparent text-slate-500 hover:text-blue-600 hover:bg-blue-50",
        success: "bg-emerald-600 hover:bg-emerald-700 text-white shadow-emerald-200 shadow-lg"
    };

    return (
        <button className={`${baseStyle} ${variants[variant]} ${className}`} disabled={isLoading} {...props}>
            {isLoading ? <Loader2 size={18} className="animate-spin" /> : Icon && <Icon size={18} />}
            {children}
        </button>
    );
};

// --- INPUTS & SELECTS ---
export const Label = ({ children }) => (
    <label className="block text-xs font-bold text-slate-500 uppercase tracking-wider mb-1.5 ml-1">
        {children}
    </label>
);

export const Select = ({ value, onChange, options, placeholder = "Selecione...", className = "" }) => (
    <div className="relative">
        <select
            value={value}
            onChange={onChange}
            className={`w-full appearance-none bg-slate-50 border border-slate-200 text-slate-700 text-sm rounded-xl focus:ring-2 focus:ring-blue-500 focus:border-transparent block p-3 transition-all cursor-pointer hover:bg-slate-100 ${className}`}
        >
            <option value="" disabled>{placeholder}</option>
            {options.map((opt) => (
                <option key={opt.value} value={opt.value}>{opt.label}</option>
            ))}
        </select>
        <div className="absolute inset-y-0 right-0 flex items-center px-3 pointer-events-none text-slate-400">
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M19 9l-7 7-7-7"></path></svg>
        </div>
    </div>
);

export const Input = ({ type = "text", value, onChange, placeholder, className = "" }) => (
    <input
        type={type}
        value={value}
        onChange={onChange}
        placeholder={placeholder}
        className={`bg-slate-50 border border-slate-200 text-slate-700 text-sm rounded-xl focus:ring-2 focus:ring-blue-500 focus:border-transparent block w-full p-3 transition-all hover:bg-slate-100 ${className}`}
    />
);

// --- BADGES ---
export const Badge = ({ type = "default", children }) => {
    const styles = {
        success: "bg-emerald-100 text-emerald-700 border-emerald-200",
        warning: "bg-amber-100 text-amber-700 border-amber-200",
        error: "bg-rose-100 text-rose-700 border-rose-200",
        neutral: "bg-slate-100 text-slate-600 border-slate-200",
        info: "bg-blue-100 text-blue-700 border-blue-200",
    };

    return (
        <span className={`px-2.5 py-0.5 rounded-full text-xs font-bold border ${styles[type] || styles.neutral}`}>
            {children}
        </span>
    );
};