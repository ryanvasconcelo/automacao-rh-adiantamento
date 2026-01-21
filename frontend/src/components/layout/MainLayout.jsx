// frontend/src/components/layout/MainLayout.jsx
import React, { useState } from 'react';
import { CollapsibleSidebar } from '../ui/Shared';
import { motion, AnimatePresence } from 'framer-motion';

export const MainLayout = ({ children, activeModule, onChangeModule }) => {
    const [isSidebarOpen, setIsSidebarOpen] = useState(true);

    return (
        <div className="min-h-screen bg-[#F8FAFC] flex font-sans text-slate-900">
            <CollapsibleSidebar
                activeModule={activeModule}
                onChangeModule={onChangeModule}
                isOpen={isSidebarOpen}
                toggleSidebar={() => setIsSidebarOpen(!isSidebarOpen)}
            />

            <motion.main
                animate={{ marginLeft: isSidebarOpen ? 280 : 80 }}
                className="flex-1 p-8 overflow-x-hidden transition-all duration-300 ease-in-out"
            >
                <AnimatePresence mode="wait">
                    <motion.div
                        key={activeModule}
                        initial={{ opacity: 0, x: 20 }}
                        animate={{ opacity: 1, x: 0 }}
                        exit={{ opacity: 0, x: -20 }}
                        transition={{ duration: 0.3 }}
                        className="max-w-[1400px] mx-auto"
                    >
                        {children}
                    </motion.div>
                </AnimatePresence>
            </motion.main>
        </div>
    );
};