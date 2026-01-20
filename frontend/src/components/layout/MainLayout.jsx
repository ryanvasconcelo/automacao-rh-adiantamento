import React from 'react';
import { Sidebar } from './Sidebar';
import { motion, AnimatePresence } from 'framer-motion';

export const MainLayout = ({ children, activeModule, onChangeModule }) => {
    return (
        <div className="min-h-screen bg-slate-50 flex">
            <Sidebar activeModule={activeModule} onChangeModule={onChangeModule} />

            <main className="flex-1 ml-72 p-8 overflow-x-hidden">
                <AnimatePresence mode="wait">
                    <motion.div
                        key={activeModule}
                        initial={{ opacity: 0, x: 10 }}
                        animate={{ opacity: 1, x: 0 }}
                        exit={{ opacity: 0, x: -10 }}
                        transition={{ duration: 0.2 }}
                        className="max-w-7xl mx-auto"
                    >
                        {children}
                    </motion.div>
                </AnimatePresence>
            </main>
        </div>
    );
};