// frontend/src/components/FopagAuditDashboard.jsx
import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { Search, AlertTriangle, Users, FileWarning, CheckCircle, XCircle, ChevronDown, ChevronUp, Info, Calculator, Hash, HelpCircle, Filter } from 'lucide-react';

// --- CONFIGURAÇÃO CORRETA ---
const API_URL = 'http://localhost:8001';

export default function FopagAuditDashboard() {
    const [loading, setLoading] = useState(false);
    const [data, setData] = useState(null);
    const [error, setError] = useState(null);

    const [company, setCompany] = useState('');
    const [month, setMonth] = useState(new Date().getMonth() + 1); // Mês atual sugerido
    const [year, setYear] = useState(new Date().getFullYear());
    const [casoPensao, setCasoPensao] = useState(2);

    const [companiesList, setCompaniesList] = useState([]);
    const [showOnlyErrors, setShowOnlyErrors] = useState(false);
    const [expandedRows, setExpandedRows] = useState({});
    const [showPensaoInfo, setShowPensaoInfo] = useState(false);

    // --- CARREGAR EMPRESAS ---
    useEffect(() => {
        const fetchCompanies = async () => {
            try {
                // CORREÇÃO CRÍTICA: Rota atualizada para /audit/fopag/companies
                const response = await axios.get(`${API_URL}/audit/fopag/companies`);
                setCompaniesList(response.data);
            } catch (error) {
                console.error("Erro ao carregar empresas", error);
                // Se falhar, mostra o fallback para sabermos que deu erro
                setCompaniesList([{ id: 'JR', name: 'JR (Modo Fallback - Erro de Conexão)' }]);
            }
        };
        fetchCompanies();
    }, []);

    const handleAudit = async () => {
        if (!company) {
            alert("Por favor, selecione uma empresa.");
            return;
        }

        setLoading(true);
        setError(null);
        setData(null);

        try {
            // CORREÇÃO CRÍTICA: Rota atualizada para /audit/fopag/audit/database
            const response = await axios.post(`${API_URL}/audit/fopag/audit/database`, {
                empresa_id: company,
                month: parseInt(month),
                year: parseInt(year),
                pension_rule: String(casoPensao)
            });

            setData(response.data);

            const temErro = response.data.divergencias?.some(d => d.tem_divergencia);
            if (temErro) setShowOnlyErrors(true);

        } catch (err) {
            console.error("Erro na auditoria:", err);
            let msg = "Erro ao conectar com o servidor.";

            if (err.response?.data?.detail) {
                const detail = err.response.data.detail;
                msg = typeof detail === 'object' ? JSON.stringify(detail) : detail;
            } else if (err.message) {
                msg = err.message;
            }

            setError(msg);
        } finally {
            setLoading(false);
        }
    };

    const toggleRow = (matricula) => {
        setExpandedRows(prev => ({ ...prev, [matricula]: !prev[matricula] }));
    };

    const formatMoney = (val) => {
        return val.toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' });
    };

    const funcionariosComErro = data?.divergencias.filter(f => f.tem_divergencia).length || 0;
    const funcionariosOK = data?.divergencias.filter(f => !f.tem_divergencia).length || 0;
    const totalEventosAuditados = data?.divergencias.reduce((acc, f) => acc + f.itens.length, 0) || 0;

    const listaExibicao = data?.divergencias.filter(func => {
        if (showOnlyErrors) return func.tem_divergencia;
        return true;
    });

    return (
        <div className="p-6 bg-gray-50 min-h-screen font-sans text-slate-800">
            <div className="bg-white p-6 rounded-xl shadow-sm mb-8 border border-gray-100">
                <h1 className="text-2xl font-bold text-gray-800 mb-6 flex items-center gap-2">
                    <Calculator className="text-blue-600" />
                    Auditoria FOPAG - Relatório Detalhado
                </h1>

                <div className="flex flex-wrap gap-4 items-end">
                    {/* DROP DOWN DE EMPRESAS */}
                    <div>
                        <label className="block text-sm font-medium text-gray-700 mb-1">Empresa</label>
                        <select
                            value={company}
                            onChange={e => setCompany(e.target.value)}
                            className="p-2.5 border border-gray-300 rounded-lg w-64 bg-white focus:ring-2 focus:ring-blue-500 outline-none"
                        >
                            <option value="">Selecione a empresa...</option>
                            {companiesList.map((emp) => (
                                <option key={emp.id} value={emp.id}>
                                    {emp.name}
                                </option>
                            ))}
                        </select>
                    </div>

                    <div>
                        <label className="block text-sm font-medium text-gray-700 mb-1">Mês</label>
                        <input type="number" value={month} onChange={e => setMonth(e.target.value)} min="1" max="12" className="p-2.5 border border-gray-300 rounded-lg w-20 text-center" />
                    </div>

                    <div>
                        <label className="block text-sm font-medium text-gray-700 mb-1">Ano</label>
                        <input type="number" value={year} onChange={e => setYear(e.target.value)} className="p-2.5 border border-gray-300 rounded-lg w-24 text-center" />
                    </div>

                    <div className="relative">
                        <label className="block text-sm font-medium text-gray-700 mb-1 flex items-center gap-1">
                            Regra de Pensão <button onClick={() => setShowPensaoInfo(!showPensaoInfo)}><Info size={16} /></button>
                        </label>
                        <select value={casoPensao} onChange={e => setCasoPensao(e.target.value)} className="p-2.5 border border-gray-300 rounded-lg w-56">
                            <option value="1">Caso 1 - Proventos Brutos</option>
                            <option value="2">Caso 2 - Líquido (Padrão)</option>
                            <option value="3">Caso 3 - Salário Base</option>
                        </select>
                        {showPensaoInfo && (
                            <div className="absolute z-10 mt-2 p-4 bg-white border border-gray-200 rounded-lg shadow-xl w-80 text-sm">
                                <p className="font-bold mb-2 border-b pb-1">Regras:</p>
                                <ul className="space-y-1 text-gray-600">
                                    <li><b>Caso 1:</b> Proventos Brutos × %</li>
                                    <li><b>Caso 2:</b> (Proventos - INSS - IRRF) × %</li>
                                    <li><b>Caso 3:</b> Salário Base × %</li>
                                </ul>
                            </div>
                        )}
                    </div>

                    <button onClick={handleAudit} disabled={loading} className="flex items-center gap-2 bg-blue-600 hover:bg-blue-700 disabled:bg-blue-300 text-white px-6 py-2.5 rounded-lg font-semibold shadow-sm transition-all">
                        {loading ? 'Processando...' : <><Search size={18} /> Auditar</>}
                    </button>
                </div>

                {error && (
                    <div className="mt-6 p-4 bg-red-50 border border-red-200 text-red-800 rounded-lg flex items-start gap-3">
                        <AlertTriangle size={20} className="mt-0.5 flex-shrink-0 text-red-600" />
                        <span className="font-medium">{error}</span>
                    </div>
                )}
            </div>

            {data && (
                <div className="space-y-6">
                    <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
                        <CardKPI title="Total Funcionários" value={data.metadata.total_funcionarios} icon={<Users className="text-blue-600" />} bgIcon="bg-blue-50" />
                        <CardKPI title="Com Divergência" value={funcionariosComErro} icon={<XCircle className="text-red-600" />} color="text-red-600" bgIcon="bg-red-50" />
                        <CardKPI title="100% Conformes" value={funcionariosOK} icon={<CheckCircle className="text-green-600" />} color="text-green-600" bgIcon="bg-green-50" />
                        <CardKPI title="Eventos Auditados" value={totalEventosAuditados} icon={<FileWarning className="text-purple-600" />} color="text-purple-600" bgIcon="bg-purple-50" />
                    </div>

                    <div className="flex justify-between items-center bg-white p-4 rounded-t-xl border-b border-gray-200 shadow-sm">
                        <h3 className="font-bold text-gray-800 flex items-center gap-2"><Users size={20} className="text-gray-500" /> Resultados</h3>
                        <button onClick={() => setShowOnlyErrors(!showOnlyErrors)} className={`flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium border ${showOnlyErrors ? 'bg-red-50 border-red-200 text-red-700' : 'bg-white border-gray-300'}`}>
                            <Filter size={16} /> {showOnlyErrors ? 'Mostrando Pendências' : 'Mostrar Todos'}
                        </button>
                    </div>

                    <div className="bg-white rounded-b-xl shadow-sm border border-gray-100 overflow-hidden">
                        {listaExibicao?.length === 0 ? (
                            <div className="p-12 text-center text-gray-500">
                                <CheckCircle size={48} className="mx-auto text-green-400 mb-4" />
                                <p className="text-lg font-medium">Tudo Certo! Nenhuma divergência encontrada.</p>
                            </div>
                        ) : (
                            <div className="divide-y divide-gray-100">
                                {listaExibicao.map((func) => (
                                    <div key={func.matricula} className="group hover:bg-slate-50">
                                        <div onClick={() => toggleRow(func.matricula)} className={`p-4 flex items-center justify-between cursor-pointer border-l-4 ${func.tem_divergencia ? 'border-l-red-500 bg-red-50/20' : 'border-l-green-500'}`}>
                                            <div className="flex items-center gap-4">
                                                {func.tem_divergencia ? <div className="bg-red-100 p-2 rounded-full"><XCircle className="text-red-600" size={20} /></div> : <div className="bg-green-100 p-2 rounded-full"><CheckCircle className="text-green-600" size={20} /></div>}
                                                <div>
                                                    <p className="font-bold text-gray-800">{func.nome}</p>
                                                    <p className="text-xs text-gray-500 font-mono">Matrícula: {func.matricula}</p>
                                                </div>
                                            </div>
                                            <div className="flex items-center gap-3">
                                                <span className={`text-sm px-3 py-1 rounded-full font-medium ${func.tem_divergencia ? 'text-red-700 bg-red-100' : 'text-green-700 bg-green-100'}`}>{func.tem_divergencia ? 'Pendência' : 'Conforme'}</span>
                                                <div className="text-gray-400">{expandedRows[func.matricula] ? <ChevronUp size={20} /> : <ChevronDown size={20} />}</div>
                                            </div>
                                        </div>

                                        {expandedRows[func.matricula] && (
                                            <div className="bg-slate-50 p-6 border-t border-gray-200">
                                                <table className="w-full text-sm bg-white rounded-lg border overflow-hidden shadow-sm">
                                                    <thead className="bg-gray-100 text-gray-500 uppercase text-xs">
                                                        <tr>
                                                            <th className="px-6 py-3 text-left">Evento</th>
                                                            <th className="px-6 py-3 text-right">Base</th>
                                                            <th className="px-6 py-3 text-right">Esperado</th>
                                                            <th className="px-6 py-3 text-right">Real</th>
                                                            <th className="px-6 py-3 text-center">Status</th>
                                                            <th className="px-6 py-3 text-right">Diferença</th>
                                                            <th className="px-6 py-3 text-center">Info</th>
                                                        </tr>
                                                    </thead>
                                                    <tbody className="divide-y divide-gray-100">
                                                        {func.itens.map((item, idx) => (
                                                            <tr key={idx} className={item.status === "ERRO" ? 'bg-red-50/50' : ''}>
                                                                <td className="px-6 py-3 font-semibold text-gray-700">{item.evento}</td>
                                                                <td className="px-6 py-3 text-right font-mono text-gray-500">{item.base > 0 ? formatMoney(item.base) : '-'}</td>
                                                                <td className="px-6 py-3 text-right font-mono text-blue-600 font-bold">{formatMoney(item.esperado)}</td>
                                                                <td className="px-6 py-3 text-right font-mono text-gray-700">{formatMoney(item.real)}</td>
                                                                <td className="px-6 py-3 text-center">
                                                                    {item.status === "OK" ? <span className="text-green-600 font-bold text-xs">OK</span> : <span className="text-red-600 font-bold text-xs bg-red-100 px-2 py-1 rounded">ERRO</span>}
                                                                </td>
                                                                <td className={`px-6 py-3 text-right font-mono font-bold ${item.status === "ERRO" ? 'text-red-600' : 'text-gray-300'}`}>{item.diferenca !== 0 ? formatMoney(item.diferenca) : '-'}</td>
                                                                <td className="px-6 py-3 text-center">{item.formula && <div className="group relative inline-block"><HelpCircle size={16} className="text-gray-400 cursor-help" /><div className="absolute bottom-full mb-2 left-1/2 -translate-x-1/2 w-48 bg-gray-800 text-white text-xs p-2 rounded opacity-0 group-hover:opacity-100 pointer-events-none transition-opacity z-50">{item.formula}</div></div>}</td>
                                                            </tr>
                                                        ))}
                                                    </tbody>
                                                </table>
                                            </div>
                                        )}
                                    </div>
                                ))}
                            </div>
                        )}
                    </div>
                </div>
            )}
        </div>
    );
}

function CardKPI({ title, value, icon, color = "text-gray-800", bgIcon }) {
    return (
        <div className="bg-white p-6 rounded-xl shadow-sm border border-gray-100 flex items-center gap-4 hover:shadow-md transition-shadow">
            <div className={`p-4 rounded-full ${bgIcon}`}>{icon}</div>
            <div>
                <p className="text-xs text-gray-500 uppercase tracking-wide font-semibold mb-1">{title}</p>
                <p className={`text-3xl font-extrabold ${color}`}>{value}</p>
            </div>
        </div>
    );
}