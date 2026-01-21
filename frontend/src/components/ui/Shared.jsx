// frontend/src/components/ui/Shared.jsx
import React, { useState, useRef, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Loader2, ChevronDown, X, Hash, Calendar, Check, ChevronRight, ChevronLeft, Search, LayoutDashboard, CalendarClock, Calculator } from 'lucide-react';
import logoProjecont from '../../assets/logoProjecont.jpeg';

// --- WRAPPER DE ANIMAÇÃO ---
export const PageTransition = ({ children, className = "" }) => (
    <motion.div
        initial={{ opacity: 0, y: 15 }}
        animate={{ opacity: 1, y: 0 }}
        exit={{ opacity: 0, y: -15 }}
        transition={{ duration: 0.4, ease: [0.22, 1, 0.36, 1] }}
        className={className}
    >
        {children}
    </motion.div>
);

// --- SIDEBAR MODERNA ---
export const CollapsibleSidebar = ({ activeModule, onChangeModule, isOpen, toggleSidebar }) => {
    const menuItems = [
        { id: 'HOME', label: 'Início', icon: LayoutDashboard },
        { id: 'ADIANTAMENTO', label: 'Adiantamento', icon: CalendarClock },
        { id: 'FOPAG', label: 'Folha Mensal', icon: Calculator },
    ];

    return (
        <motion.aside
            initial={false}
            animate={{ width: isOpen ? 280 : 80 }}
            className="bg-slate-900 text-white flex flex-col h-screen fixed left-0 top-0 shadow-2xl z-40 overflow-hidden transition-all duration-300 border-r border-slate-800"
        >
            <div className="p-6 flex items-center gap-4 h-24 relative">
                <img src={logoProjecont} alt="GLF" className="w-10 h-10 rounded-lg shadow-lg shadow-blue-500/20 flex-shrink-0" />
                {isOpen && (
                    <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="whitespace-nowrap overflow-hidden">
                        <h1 className="text-xl font-bold tracking-tight">GFS Auditoria</h1>
                        <p className="text-xs text-slate-400">Projecont RH Tools</p>
                    </motion.div>
                )}
            </div>

            {/* Botão de Toggle (Z-Index alto para ficar sobre o body e a sidebar) */}
            <button
                onClick={toggleSidebar}
                className="absolute top-9 -right-3 bg-blue-600 text-white p-1.5 rounded-full shadow-lg border-2 border-slate-50 transition-all hover:bg-blue-500 hover:scale-110 z-50 flex items-center justify-center cursor-pointer"
                style={{ transform: 'translateX(-50%)' }}
            >
                {isOpen ? <ChevronLeft size={14} /> : <ChevronRight size={14} />}
            </button>

            <nav className="flex-1 px-3 py-8 space-y-2">
                {menuItems.map((item) => {
                    const isActive = activeModule === item.id;
                    const Icon = item.icon;
                    return (
                        <button
                            key={item.id}
                            onClick={() => onChangeModule(item.id)}
                            className={`w-full flex items-center gap-4 px-3 py-3 rounded-xl transition-all duration-200 group relative overflow-hidden ${isActive ? 'bg-blue-600 text-white shadow-lg shadow-blue-900/50' : 'text-slate-400 hover:bg-slate-800 hover:text-white'
                                }`}
                        >
                            <div className="flex-shrink-0 w-8 flex justify-center">
                                <Icon size={20} />
                            </div>
                            {isOpen && (
                                <motion.span initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="font-medium whitespace-nowrap">
                                    {item.label}
                                </motion.span>
                            )}
                            {isActive && !isOpen && <div className="absolute right-2 w-1.5 h-1.5 bg-white rounded-full" />}
                        </button>
                    );
                })}
            </nav>
        </motion.aside>
    );
};

// --- DROPDOWN COM PESQUISA (Maior e Searchable) ---
export const CustomSelect = ({ value, onChange, options, label, placeholder = "Selecione...", searchable = true }) => {
    const [isOpen, setIsOpen] = useState(false);
    const [search, setSearch] = useState("");
    const ref = useRef(null);

    useEffect(() => {
        const handleClickOutside = (event) => { if (ref.current && !ref.current.contains(event.target)) setIsOpen(false); };
        document.addEventListener("mousedown", handleClickOutside);
        return () => document.removeEventListener("mousedown", handleClickOutside);
    }, []);

    const filteredOptions = options.filter(opt =>
        opt.label.toLowerCase().includes(search.toLowerCase())
    );

    const selectedLabel = options.find(o => String(o.value) === String(value))?.label || placeholder;

    return (
        <div className="relative w-full" ref={ref}>
            {label && <label className="block text-xs font-bold text-slate-500 uppercase tracking-wider mb-1.5 ml-1">{label}</label>}
            <button
                onClick={() => setIsOpen(!isOpen)}
                className={`w-full flex items-center justify-between bg-white border ${isOpen ? 'border-blue-500 ring-2 ring-blue-100' : 'border-slate-200'} text-slate-700 text-sm rounded-xl p-3 transition-all hover:border-blue-300 hover:shadow-sm`}
            >
                <span className="truncate">{selectedLabel}</span>
                <ChevronDown size={16} className={`text-slate-400 transition-transform duration-300 ${isOpen ? 'rotate-180' : ''}`} />
            </button>

            <AnimatePresence>
                {isOpen && (
                    <motion.div
                        initial={{ opacity: 0, y: -10, scale: 0.98 }}
                        animate={{ opacity: 1, y: 0, scale: 1 }}
                        exit={{ opacity: 0, y: -10, scale: 0.98 }}
                        transition={{ duration: 0.15 }}
                        className="absolute z-50 w-full mt-2 bg-white border border-slate-100 rounded-xl shadow-2xl overflow-hidden"
                    >
                        {searchable && (
                            <div className="p-2 border-b border-slate-100 bg-slate-50 sticky top-0">
                                <div className="relative">
                                    <Search size={14} className="absolute left-3 top-2.5 text-slate-400" />
                                    <input
                                        autoFocus
                                        type="text"
                                        placeholder="Filtrar..."
                                        value={search}
                                        onChange={(e) => setSearch(e.target.value)}
                                        className="w-full pl-8 pr-3 py-1.5 text-sm bg-white border border-slate-200 rounded-lg focus:outline-none focus:border-blue-400"
                                    />
                                </div>
                            </div>
                        )}

                        <div className="max-h-96 overflow-y-auto">
                            {filteredOptions.length > 0 ? filteredOptions.map((opt) => (
                                <div
                                    key={opt.value}
                                    onClick={() => { onChange(opt.value); setIsOpen(false); setSearch(""); }}
                                    className={`px-4 py-2.5 text-sm cursor-pointer flex items-center justify-between hover:bg-blue-50 transition-colors ${String(value) === String(opt.value) ? 'bg-blue-50/50 text-blue-700 font-medium' : 'text-slate-600'}`}
                                >
                                    {opt.label}
                                    {String(value) === String(opt.value) && <Check size={14} className="text-blue-600" />}
                                </div>
                            )) : <div className="p-4 text-center text-xs text-slate-400">Nenhuma opção encontrada</div>}
                        </div>
                    </motion.div>
                )}
            </AnimatePresence>
        </div>
    );
};

// --- DATA PICKER (Limitado Ano Atual) ---
export const MonthYearPicker = ({ month, year, onMonthChange, onYearChange }) => {
    const currentYear = new Date().getFullYear();
    const months = [{ v: 1, l: 'Jan' }, { v: 2, l: 'Fev' }, { v: 3, l: 'Mar' }, { v: 4, l: 'Abr' }, { v: 5, l: 'Mai' }, { v: 6, l: 'Jun' }, { v: 7, l: 'Jul' }, { v: 8, l: 'Ago' }, { v: 9, l: 'Set' }, { v: 10, l: 'Out' }, { v: 11, l: 'Nov' }, { v: 12, l: 'Dez' }];

    return (
        <div className="flex gap-2 items-end">
            <div className="w-24"><CustomSelect label="Mês" value={month} onChange={onMonthChange} options={months.map(m => ({ value: m.v, label: m.l }))} searchable={false} /></div>
            <div className="w-28">
                <label className="block text-xs font-bold text-slate-500 uppercase tracking-wider mb-1.5 ml-1">Ano</label>
                <div className="relative">
                    <input
                        type="number"
                        value={year}
                        max={currentYear}
                        onChange={(e) => {
                            const val = parseInt(e.target.value);
                            if (val > currentYear) return;
                            onYearChange(val);
                        }}
                        className="w-full bg-white border border-slate-200 text-slate-700 text-sm rounded-xl p-3 pl-9 focus:ring-2 focus:ring-blue-100 focus:border-blue-500 transition-all font-mono"
                    />
                    <Calendar size={16} className="absolute left-3 top-3 text-slate-400" />
                </div>
            </div>
        </div>
    );
};

// --- SMART BUTTON (Animação de Frases dentro do botão) ---
export const SmartButton = ({ onClick, isLoading, icon: Icon, children, className = "", variant = "primary" }) => {
    const phrases = [
        "Conectando ao Fortes...",
        "Analisando Colaboradores...",
        "Calculando Verbas...",
        "Verificando Regras...",
        "Consolidando..."
    ];
    const [index, setIndex] = useState(0);

    useEffect(() => {
        if (!isLoading) { setIndex(0); return; }
        const interval = setInterval(() => setIndex((p) => (p + 1) % phrases.length), 2000);
        return () => clearInterval(interval);
    }, [isLoading]);

    const variants = {
        primary: "bg-blue-600 hover:bg-blue-700 text-white shadow-lg shadow-blue-200",
        green: "bg-green-600 hover:bg-green-700 text-white shadow-lg shadow-green-200"
    };

    return (
        <button
            onClick={onClick}
            disabled={isLoading}
            className={`w-full inline-flex items-center justify-center gap-2 px-5 py-3.5 rounded-xl font-semibold transition-all duration-200 active:scale-95 disabled:opacity-80 disabled:cursor-wait text-base ${variants[variant] || variants.primary} ${className}`}
        >
            {isLoading ? (
                <div className="flex items-center gap-3">
                    <Loader2 size={18} className="animate-spin" />
                    <span className="animate-fade-in key={index} min-w-[160px] text-left">{phrases[index]}</span>
                </div>
            ) : (
                <>
                    {Icon && <Icon size={18} />}
                    {children}
                </>
            )}
        </button>
    );
};

export const SmartLoading = () => null; // Depreciado em favor do SmartButton

export const Card = ({ children, className = "", noPadding = false, onClick }) => (
    <motion.div
        onClick={onClick}
        initial={{ opacity: 0, scale: 0.99 }}
        animate={{ opacity: 1, scale: 1 }}
        className={`bg-white rounded-2xl border border-slate-200/60 shadow-sm transition-all duration-300 overflow-hidden ${className}`}
    >
        <div className={noPadding ? "" : "p-6"}>{children}</div>
    </motion.div>
);

export const Button = ({ children, variant = "primary", icon: Icon, onClick, className = "" }) => {
    const style = variant === 'ghost' ? "bg-transparent text-slate-500 hover:text-blue-600" :
        variant === 'success' ? "bg-emerald-600 text-white hover:bg-emerald-700 shadow-emerald-200 shadow-lg" :
            variant === 'secondary' ? "bg-white border border-slate-200 text-slate-700 hover:bg-slate-50" :
                "bg-blue-600 text-white hover:bg-blue-700";

    return (
        <button onClick={onClick} className={`inline-flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-colors ${style} ${className}`}>
            {Icon && <Icon size={16} />} {children}
        </button>
    )
}

export const Badge = ({ type = "default", children }) => {
    const styles = {
        success: "bg-emerald-50 text-emerald-700 border-emerald-100 ring-1 ring-emerald-200/50",
        warning: "bg-amber-50 text-amber-700 border-amber-100 ring-1 ring-amber-200/50",
        error: "bg-rose-50 text-rose-700 border-rose-100 ring-1 ring-rose-200/50",
        neutral: "bg-slate-50 text-slate-600 border-slate-200",
    };
    return <span className={`px-2.5 py-1 rounded-lg text-xs font-bold border ${styles[type]}`}>{children}</span>;
};

export const Input = ({ type = "text", value, onChange, placeholder, className = "" }) => (
    <input
        type={type}
        value={value}
        onChange={onChange}
        placeholder={placeholder}
        className={`bg-slate-50 border border-slate-200 text-slate-700 text-sm rounded-xl focus:ring-2 focus:ring-blue-500 focus:border-transparent block w-full p-3 transition-all hover:bg-slate-100 ${className}`}
    />
);

export const Toggle = ({ enabled, onChange, label }) => (
    <div className="flex items-center cursor-pointer group" onClick={() => onChange(!enabled)}>
        <div className={`relative w-11 h-6 rounded-full transition-colors duration-200 ease-in-out ${enabled ? 'bg-emerald-500' : 'bg-slate-300 group-hover:bg-slate-400'}`}>
            <motion.div
                layout
                transition={{ type: "spring", stiffness: 700, damping: 30 }}
                className={`absolute top-1 left-1 bg-white w-4 h-4 rounded-full shadow-sm`}
                animate={{ x: enabled ? 20 : 0 }}
            />
        </div>
        {label && <span className={`ml-3 text-sm font-medium ${enabled ? 'text-emerald-700' : 'text-slate-500'}`}>{label}</span>}
    </div>
);

// --- MODAL DE DETALHES DE CÁLCULO ---
export const CalculationModal = ({ isOpen, onClose, data }) => {
    if (!isOpen || !data) return null;

    return (
        <div className="fixed inset-0 z-[100] flex items-center justify-center p-4 bg-slate-900/60 backdrop-blur-sm animate-fade-in" onClick={onClose}>
            <motion.div
                initial={{ opacity: 0, scale: 0.95, y: 20 }}
                animate={{ opacity: 1, scale: 1, y: 0 }}
                onClick={(e) => e.stopPropagation()}
                className="bg-white w-full max-w-lg rounded-2xl shadow-2xl overflow-hidden border border-slate-100"
            >
                {/* Header */}
                <div className="bg-slate-50 px-6 py-4 border-b border-slate-100 flex justify-between items-center">
                    <div>
                        <h3 className="text-lg font-bold text-slate-800">{data.tipo || "Detalhes do Cálculo"}</h3>
                        <p className="text-xs text-slate-500 uppercase tracking-wider font-semibold">Memória de Auditoria</p>
                    </div>
                    <button onClick={onClose} className="p-2 hover:bg-slate-200 rounded-full transition-colors">
                        <X size={20} className="text-slate-400" />
                    </button>
                </div>

                {/* Body */}
                <div className="p-6 space-y-6">
                    {/* Variáveis */}
                    <div>
                        <h4 className="text-xs font-bold text-slate-400 uppercase mb-3 flex items-center gap-2">
                            <Hash size={12} /> Variáveis Utilizadas
                        </h4>
                        <div className="grid grid-cols-2 gap-3">
                            {data.variaveis?.map((v, i) => (
                                <div key={i} className="bg-slate-50 p-3 rounded-xl border border-slate-100">
                                    <p className="text-[10px] text-slate-500 font-semibold uppercase">{v.nome}</p>
                                    <p className="text-sm font-mono font-bold text-slate-700">{v.valor}</p>
                                </div>
                            ))}
                        </div>
                    </div>

                    {/* Passos */}
                    {data.passos && (
                        <div>
                            <h4 className="text-xs font-bold text-slate-400 uppercase mb-3 flex items-center gap-2">
                                <Calculator size={12} /> Roteiro de Cálculo
                            </h4>
                            <ul className="space-y-2">
                                {data.passos.map((p, i) => (
                                    <li key={i} className="text-xs text-slate-600 font-mono bg-blue-50/50 p-2 rounded-lg border border-blue-100 flex gap-2">
                                        <span className="text-blue-400 font-bold">{i + 1}.</span> {p}
                                    </li>
                                ))}
                            </ul>
                        </div>
                    )}

                    {/* Resultado */}
                    <div className="bg-slate-900 text-white p-4 rounded-xl flex justify-between items-center shadow-lg">
                        <span className="text-xs font-bold uppercase text-slate-400">Resultado Esperado</span>
                        <span className="text-xl font-mono font-bold text-emerald-400">{data.resultado}</span>
                    </div>
                </div>
            </motion.div>
        </div>
    );
};