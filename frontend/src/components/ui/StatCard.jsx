// src/components/ui/StatCard.jsx
import React from 'react';
import { motion } from 'framer-motion';

export const StatCard = ({ title, value, icon: Icon, color = "blue", subtext }) => {
    const colorStyles = {
        blue: "bg-blue-50 text-blue-700 border-blue-100",
        green: "bg-emerald-50 text-emerald-700 border-emerald-100",
        red: "bg-rose-50 text-rose-700 border-rose-100",
        purple: "bg-purple-50 text-purple-700 border-purple-100",
        gray: "bg-white text-slate-700 border-slate-200",
    };

    return (
        <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            className={`p-6 rounded-2xl border shadow-sm hover:shadow-md transition-all duration-300 ${colorStyles[color] || colorStyles.gray}`}
        >
            <div className="flex items-center justify-between mb-4">
                <p className="text-xs font-bold uppercase tracking-wider opacity-70">{title}</p>
                {Icon && <Icon size={20} className="opacity-80" />}
            </div>
            <div className="flex items-end gap-2">
                <h3 className="text-3xl font-bold tracking-tight">{value}</h3>
                {subtext && <span className="text-xs font-medium opacity-60 mb-1">{subtext}</span>}
            </div>
        </motion.div>
    );
};