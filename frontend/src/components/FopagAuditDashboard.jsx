// frontend/src/components/FopagAuditDashboard.jsx
import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { Search, ChevronDown, ChevronUp, Play, Calculator, HelpCircle, AlertTriangle } from 'lucide-react';
import { PageTransition, Card, Button, Label, Select, Input, Badge } from './ui/Shared';
import { StatCard } from './ui/StatCard';

const API_URL = 'http://localhost:8001';

export default function FopagAuditDashboard() {
    const [loading, setLoading] = useState(false);
    const [data, setData] = useState(null);
    const [error, setError] = useState(null);

    const [company, setCompany] = useState('');
    const [month, setMonth] = useState(new Date().getMonth() + 1);
    const [year, setYear] = useState(new Date().getFullYear());
    const [pensionRule, setPensionRule] = useState('2');
    const [companiesList, setCompaniesList] = useState([]);
    const [expandedRows, setExpandedRows] = useState({});
    const [showErrorsOnly, setShowErrorsOnly] = useState(false);

    useEffect(() => {
        axios.get(`${API_URL}/audit/fopag/companies`)
            .then(res => setCompaniesList(res.data))
            .catch(() => setCompaniesList([{ id: 'JR', name: 'JR (Fallback)' }]));
    }, []);

    const handleAudit = async () => {
        if (!company) return;
        setLoading(true); setError(null); setData(null);
        try {
            const res = await axios.post(`${API_URL}/audit/fopag/audit/database`, {
                empresa_id: company, month: parseInt(month), year: parseInt(year), pension_rule: pensionRule
            });
            setData(res.data);
            if (res.data.divergencias.some(d => d.tem_divergencia)) setShowErrorsOnly(true);
        } catch (err) {
            setError(err.response?.data?.detail || "Erro ao conectar com o servidor.");
        } finally { setLoading(false); }
    };

    const toggleRow = (id) => setExpandedRows(prev => ({ ...prev, [id]: !prev[id] }));
    const formatMoney = (val) => val?.toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' });

    // Lista Filtrada
    const filteredList = data?.divergencias.filter(f => showErrorsOnly ? f.tem_divergencia : true);

    return (
        <PageTransition className="space-y-6">
            <Card>
                <div className="flex flex-wrap items-end gap-4">
                    <div className="flex-1 min-w-[200px]">
                        <Label>Empresa</Label>
                        <Select
                            value={company}
                            onChange={e => setCompany(e.target.value)}
                            options={companiesList.map(c => ({ value: c.id, label: c.name }))}
                        />
                    </div>
                    <div className="w-24">
                        <Label>Mês</Label>
                        <Input type="number" value={month} onChange={e => setMonth(e.target.value)} />
                    </div>
                    <div className="w-28">
                        <Label>Ano</Label>
                        <Input type="number" value={year} onChange={e => setYear(e.target.value)} />
                    </div>
                    <div className="w-48">
                        <Label>Regra Pensão</Label>
                        <Select
                            value={pensionRule}
                            onChange={e => setPensionRule(e.target.value)}
                            options={[
                                { value: '1', label: '1 - Bruto' },
                                { value: '2', label: '2 - Líquido (Padrão)' },
                                { value: '3', label: '3 - Salário Base' }
                            ]}
                        />
                    </div>
                    <Button onClick={handleAudit} isLoading={loading} icon={Play} className="h-[46px]">
                        Auditar
                    </Button>
                </div>
                {error && <div className="mt-4 p-3 bg-rose-50 text-rose-700 rounded-lg text-sm border border-rose-100 flex items-center gap-2"><AlertTriangle size={16} />{error}</div>}
            </Card>

            {data && (
                <>
                    <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
                        <StatCard title="Total Funcionários" value={data.metadata.total_funcionarios} icon={UsersIcon} color="blue" />
                        <StatCard title="Divergências" value={data.metadata.total_divergencias} icon={AlertTriangle} color="red" />
                        <StatCard title="Conformes" value={data.metadata.total_funcionarios - data.metadata.total_divergencias} icon={CheckIcon} color="green" />
                    </div>

                    <Card noPadding>
                        <div className="p-4 border-b border-slate-100 flex justify-between items-center bg-slate-50/50">
                            <h3 className="font-bold text-slate-700">Resultados da Análise</h3>
                            <div className="flex bg-white rounded-lg border border-slate-200 p-1">
                                <button onClick={() => setShowErrorsOnly(false)} className={`px-3 py-1 text-xs font-bold rounded-md transition-all ${!showErrorsOnly ? 'bg-slate-100 text-slate-800' : 'text-slate-400'}`}>Todos</button>
                                <button onClick={() => setShowErrorsOnly(true)} className={`px-3 py-1 text-xs font-bold rounded-md transition-all ${showErrorsOnly ? 'bg-rose-50 text-rose-700' : 'text-slate-400'}`}>Pendências</button>
                            </div>
                        </div>

                        <div className="max-h-[600px] overflow-auto">
                            {filteredList.map(func => (
                                <div key={func.matricula} className="border-b border-slate-100 last:border-0">
                                    <div
                                        onClick={() => toggleRow(func.matricula)}
                                        className={`p-4 flex items-center justify-between cursor-pointer hover:bg-slate-50 transition-colors ${func.tem_divergencia ? 'bg-rose-50/30' : ''}`}
                                    >
                                        <div className="flex items-center gap-4">
                                            <div className={`p-2 rounded-full ${func.tem_divergencia ? 'bg-rose-100 text-rose-600' : 'bg-emerald-100 text-emerald-600'}`}>
                                                {func.tem_divergencia ? <AlertTriangle size={18} /> : <CheckIcon size={18} />}
                                            </div>
                                            <div>
                                                <p className="font-bold text-slate-800 text-sm">{func.nome}</p>
                                                <p className="text-xs text-slate-400 font-mono">{func.matricula}</p>
                                            </div>
                                        </div>

                                        <div className="flex items-center gap-4">
                                            <Badge type={func.tem_divergencia ? 'error' : 'success'}>
                                                {func.tem_divergencia ? 'Atenção' : 'Conforme'}
                                            </Badge>
                                            {expandedRows[func.matricula] ? <ChevronUp size={18} className="text-slate-400" /> : <ChevronDown size={18} className="text-slate-400" />}
                                        </div>
                                    </div>

                                    {expandedRows[func.matricula] && (
                                        <div className="bg-slate-50/50 p-4 border-t border-slate-100 shadow-inner">
                                            <table className="w-full text-xs bg-white rounded-lg shadow-sm overflow-hidden border border-slate-200">
                                                <thead className="bg-slate-100 text-slate-500 uppercase">
                                                    <tr>
                                                        <th className="px-4 py-2 text-left">Evento</th>
                                                        <th className="px-4 py-2 text-right">Base</th>
                                                        <th className="px-4 py-2 text-right text-blue-600">Esperado</th>
                                                        <th className="px-4 py-2 text-right text-slate-600">Real</th>
                                                        <th className="px-4 py-2 text-center">Status</th>
                                                        <th className="px-4 py-2 text-right">Diferença</th>
                                                        <th className="px-4 py-2 text-center">Info</th>
                                                    </tr>
                                                </thead>
                                                <tbody className="divide-y divide-slate-100">
                                                    {func.itens.map((item, idx) => (
                                                        <tr key={idx} className={item.status === "ERRO" ? "bg-rose-50" : ""}>
                                                            <td className="px-4 py-2 font-medium text-slate-700">{item.evento}</td>
                                                            <td className="px-4 py-2 text-right font-mono text-slate-400">{item.base > 0 ? formatMoney(item.base) : '-'}</td>
                                                            <td className="px-4 py-2 text-right font-mono font-bold text-blue-600">{formatMoney(item.esperado)}</td>
                                                            <td className="px-4 py-2 text-right font-mono text-slate-600">{formatMoney(item.real)}</td>
                                                            <td className="px-4 py-2 text-center">
                                                                {item.status === "OK"
                                                                    ? <span className="text-emerald-600 font-bold text-[10px]">OK</span>
                                                                    : <span className="text-rose-600 font-bold text-[10px]">ERRO</span>
                                                                }
                                                            </td>
                                                            <td className={`px-4 py-2 text-right font-mono font-bold ${item.status === 'ERRO' ? 'text-rose-600' : 'text-slate-300'}`}>
                                                                {item.diferenca !== 0 ? formatMoney(item.diferenca) : '-'}
                                                            </td>
                                                            <td className="px-4 py-2 text-center">
                                                                {item.formula && (
                                                                    <div className="group relative inline-block">
                                                                        <HelpCircle size={14} className="text-slate-300 hover:text-blue-500 cursor-help" />
                                                                        <div className="absolute bottom-full right-0 w-48 bg-slate-800 text-white p-2 rounded shadow-lg opacity-0 group-hover:opacity-100 pointer-events-none transition-opacity z-10 mb-2">
                                                                            {item.formula}
                                                                        </div>
                                                                    </div>
                                                                )}
                                                            </td>
                                                        </tr>
                                                    ))}
                                                </tbody>
                                            </table>
                                        </div>
                                    )}
                                </div>
                            ))}
                        </div>
                    </Card>
                </>
            )}
        </PageTransition>
    );
}

// Icones locais para evitar erro de import
const UsersIcon = (props) => <svg {...props} xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2" /><circle cx="9" cy="7" r="4" /><path d="M22 21v-2a4 4 0 0 0-3-3.87" /><path d="M16 3.13a4 4 0 0 1 0 7.75" /></svg>
const CheckIcon = (props) => <svg {...props} xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><polyline points="20 6 9 17 4 12" /></svg>