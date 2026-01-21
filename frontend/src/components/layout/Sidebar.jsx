import React from 'react';
import { Calculator, CalendarClock, LayoutDashboard } from 'lucide-react';
import logoProjecont from '../../assets/logoProjecont.jpeg';

export const Sidebar = ({ activeModule, onChangeModule }) => {
    const menuItems = [
        { id: 'HOME', label: 'Início', icon: LayoutDashboard },
        { id: 'ADIANTAMENTO', label: 'Adiantamento', icon: CalendarClock },
        { id: 'FOPAG', label: 'Folha Mensal', icon: Calculator },
    ];

    return (
        <aside className="w-72 bg-slate-900 text-white flex flex-col h-screen fixed left-0 top-0 shadow-2xl z-50">
            {/* Header do Menu */}
            <div className="p-8 flex items-center gap-4 border-b border-slate-800">
                <img src={logoProjecont} alt="GLF" className="w-10 h-10 rounded-lg shadow-lg shadow-blue-500/20" />
                <div>
                    <h1 className="text-xl font-bold tracking-tight">GFS Auditoria</h1>
                    <p className="text-xs text-slate-400">Projecont RH Tools</p>
                </div>
            </div>

            {/* Navegação */}
            <nav className="flex-1 px-4 py-8 space-y-2">
                <p className="px-4 text-xs font-semibold text-slate-500 uppercase tracking-widest mb-4">Módulos</p>

                {menuItems.map((item) => {
                    const isActive = activeModule === item.id;
                    const Icon = item.icon;

                    return (
                        <button
                            key={item.id}
                            onClick={() => onChangeModule(item.id)}
                            className={`w-full flex items-center gap-4 px-4 py-3.5 rounded-xl transition-all duration-200 group relative overflow-hidden ${isActive
                                ? 'bg-blue-600 text-white shadow-lg shadow-blue-900/50'
                                : 'text-slate-400 hover:bg-slate-800 hover:text-white'
                                }`}
                        >
                            <Icon size={20} className={isActive ? 'text-white' : 'text-slate-500 group-hover:text-blue-400'} />
                            <span className="font-medium">{item.label}</span>

                            {isActive && (
                                <div className="absolute right-0 top-1/2 -translate-y-1/2 w-1 h-8 bg-white/20 rounded-l-full" />
                            )}
                        </button>
                    );
                })}
            </nav>

            {/* Footer */}
            <div className="p-6 border-t border-slate-800">
                <div className="bg-slate-800/50 rounded-xl p-4 flex items-center gap-3">
                    <div className="w-8 h-8 rounded-full bg-gradient-to-tr from-blue-500 to-purple-500 flex items-center justify-center text-xs font-bold">
                        GLF
                    </div>
                    <div className="flex-1 overflow-hidden">
                        <p className="text-sm font-medium truncate">Usuário RH</p>
                        <p className="text-xs text-slate-400">Online</p>
                    </div>
                </div>
            </div>
        </aside>
    );
};