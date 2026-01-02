import React, { useState } from 'react';
import axios from 'axios';
import { Search, AlertTriangle, Users, FileWarning, CheckCircle, XCircle, ChevronDown, ChevronUp, Info, Calculator, Hash, HelpCircle, Filter } from 'lucide-react';

const API_URL = 'http://127.0.0.1:8000';

export default function FopagAuditDashboard() {
    const [loading, setLoading] = useState(false);
    const [data, setData] = useState(null);
    const [error, setError] = useState(null);

    // Filtros de Execução
    const [company, setCompany] = useState('JR');
    const [month, setMonth] = useState(11);
    const [year, setYear] = useState(2025);
    const [casoPensao, setCasoPensao] = useState(2);

    // Filtros de Visualização
    const [showOnlyErrors, setShowOnlyErrors] = useState(false); // NOVO FILTRO

    const [expandedRows, setExpandedRows] = useState({});
    const [showPensaoInfo, setShowPensaoInfo] = useState(false);

    const handleAudit = async () => {
        setLoading(true);
        setError(null);
        setData(null);
        try {
            const response = await axios.post(`${API_URL}/api/v1/fopag/audit/database`, {
                company_code: company,
                month: parseInt(month),
                year: parseInt(year),
                caso_pensao: parseInt(casoPensao)
            });
            setData(response.data);

            // Se tiver erro, já ativa o filtro automaticamente para facilitar
            const temErro = response.data.divergencias.some(d => d.tem_divergencia);
            if (temErro) setShowOnlyErrors(true);

        } catch (err) {
            console.error(err);
            setError(err.response?.data?.detail || "Erro ao conectar com o servidor.");
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

    // KPIs Gerais (Sempre calculados sobre o total)
    const funcionariosComErro = data?.divergencias.filter(f => f.tem_divergencia).length || 0;
    const funcionariosOK = data?.divergencias.filter(f => !f.tem_divergencia).length || 0;
    const totalEventosAuditados = data?.divergencias.reduce((acc, f) => acc + f.itens.length, 0) || 0;
    const totalErros = data?.divergencias.reduce((acc, f) => acc + f.itens.filter(i => i.status === "ERRO").length, 0) || 0;

    // Lista Filtrada para Exibição
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
                    <div>
                        <label className="block text-sm font-medium text-gray-700 mb-1">Empresa</label>
                        <select
                            value={company}
                            onChange={e => setCompany(e.target.value)}
                            className="p-2.5 border border-gray-300 rounded-lg w-56 bg-white focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none transition-all"
                        >
                            <option value="JR">JR RODRIGUES</option>
                            <option value="2056">A CICLISTA (2056)</option>
                            <option value="CMD">CMD (Exemplo)</option>
                        </select>
                    </div>

                    <div>
                        <label className="block text-sm font-medium text-gray-700 mb-1">Mês</label>
                        <input
                            type="number"
                            value={month}
                            onChange={e => setMonth(e.target.value)}
                            min="1"
                            max="12"
                            className="p-2.5 border border-gray-300 rounded-lg w-20 text-center focus:ring-2 focus:ring-blue-500 outline-none"
                        />
                    </div>

                    <div>
                        <label className="block text-sm font-medium text-gray-700 mb-1">Ano</label>
                        <input
                            type="number"
                            value={year}
                            onChange={e => setYear(e.target.value)}
                            className="p-2.5 border border-gray-300 rounded-lg w-24 text-center focus:ring-2 focus:ring-blue-500 outline-none"
                        />
                    </div>

                    <div className="relative">
                        <label className="block text-sm font-medium text-gray-700 mb-1 flex items-center gap-1">
                            Regra de Pensão
                            <button
                                onClick={() => setShowPensaoInfo(!showPensaoInfo)}
                                className="text-gray-400 hover:text-blue-600 transition-colors"
                            >
                                <Info size={16} />
                            </button>
                        </label>
                        <select
                            value={casoPensao}
                            onChange={e => setCasoPensao(e.target.value)}
                            className="p-2.5 border border-gray-300 rounded-lg w-56 bg-white focus:ring-2 focus:ring-blue-500 outline-none"
                        >
                            <option value="1">Caso 1 - Proventos Brutos</option>
                            <option value="2">Caso 2 - Líquido (Padrão)</option>
                            <option value="3">Caso 3 - Salário Base</option>
                        </select>

                        {showPensaoInfo && (
                            <div className="absolute z-10 mt-2 p-4 bg-white border border-gray-200 rounded-lg shadow-xl w-80 text-sm animate-fade-in-down">
                                <p className="font-bold text-gray-800 mb-2 border-b pb-1">Regras de Cálculo:</p>
                                <ul className="space-y-2 text-gray-600">
                                    <li><span className="font-semibold text-blue-600">Caso 1:</span> Proventos Brutos × %</li>
                                    <li><span className="font-semibold text-blue-600">Caso 2:</span> (Proventos - INSS - IRRF) × %</li>
                                    <li><span className="font-semibold text-blue-600">Caso 3:</span> Salário Base × %</li>
                                </ul>
                            </div>
                        )}
                    </div>

                    <button
                        onClick={handleAudit}
                        disabled={loading}
                        className="flex items-center gap-2 bg-blue-600 hover:bg-blue-700 disabled:bg-blue-300 text-white px-6 py-2.5 rounded-lg font-semibold shadow-sm transition-all active:scale-95"
                    >
                        {loading ? (
                            <>
                                <div className="animate-spin rounded-full h-4 w-4 border-2 border-white border-t-transparent"></div>
                                Processando...
                            </>
                        ) : (
                            <>
                                <Search size={18} />
                                Auditar
                            </>
                        )}
                    </button>
                </div>

                {error && (
                    <div className="mt-6 p-4 bg-red-50 border border-red-200 text-red-800 rounded-lg flex items-start gap-3 animate-shake">
                        <AlertTriangle size={20} className="mt-0.5 flex-shrink-0 text-red-600" />
                        <span className="font-medium">{error}</span>
                    </div>
                )}
            </div>

            {data && (
                <div className="animate-fade-in space-y-6">
                    {/* KPIs */}
                    <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
                        <CardKPI title="Total Funcionários" value={data.metadata.total_funcionarios} icon={<Users className="text-blue-600" />} bgIcon="bg-blue-50" />
                        <CardKPI title="Com Divergência" value={funcionariosComErro} icon={<XCircle className="text-red-600" />} color="text-red-600" bgIcon="bg-red-50" />
                        <CardKPI title="100% Conformes" value={funcionariosOK} icon={<CheckCircle className="text-green-600" />} color="text-green-600" bgIcon="bg-green-50" />
                        <CardKPI title="Eventos Auditados" value={totalEventosAuditados} icon={<FileWarning className="text-purple-600" />} color="text-purple-600" bgIcon="bg-purple-50" />
                    </div>

                    {/* Barra de Ferramentas da Tabela */}
                    <div className="flex justify-between items-center bg-white p-4 rounded-t-xl border-b border-gray-200 shadow-sm">
                        <h3 className="font-bold text-gray-800 flex items-center gap-2">
                            <Users size={20} className="text-gray-500" />
                            Resultados da Auditoria
                        </h3>

                        {/* BOTÃO DE FILTRO DE PENDÊNCIAS */}
                        <button
                            onClick={() => setShowOnlyErrors(!showOnlyErrors)}
                            className={`flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-all border ${showOnlyErrors
                                    ? 'bg-red-50 border-red-200 text-red-700 shadow-inner'
                                    : 'bg-white border-gray-300 text-gray-600 hover:bg-gray-50'
                                }`}
                        >
                            <Filter size={16} />
                            {showOnlyErrors ? 'Mostrando Apenas Pendências' : 'Mostrar Todos'}
                            {funcionariosComErro > 0 && (
                                <span className={`ml-1 px-2 py-0.5 rounded-full text-xs font-bold ${showOnlyErrors ? 'bg-red-200 text-red-800' : 'bg-gray-200 text-gray-700'
                                    }`}>
                                    {funcionariosComErro}
                                </span>
                            )}
                        </button>
                    </div>

                    {/* Lista de Funcionários */}
                    <div className="bg-white rounded-b-xl shadow-sm border border-gray-100 overflow-hidden">
                        {listaExibicao?.length === 0 ? (
                            <div className="p-12 text-center text-gray-500">
                                <CheckCircle size={48} className="mx-auto text-green-400 mb-4" />
                                <p className="text-lg font-medium">Nenhuma divergência encontrada!</p>
                                <p className="text-sm">A folha está 100% em conformidade com as regras auditadas.</p>
                            </div>
                        ) : (
                            <div className="divide-y divide-gray-100">
                                {listaExibicao.map((func) => {
                                    const errosCount = func.itens.filter(i => i.status === "ERRO").length;

                                    return (
                                        <div key={func.matricula} className="group transition-colors hover:bg-slate-50">
                                            <div
                                                onClick={() => toggleRow(func.matricula)}
                                                className={`p-4 flex items-center justify-between cursor-pointer transition-all border-l-4 ${func.tem_divergencia
                                                        ? 'border-l-red-500 bg-red-50/20'
                                                        : 'border-l-green-500 hover:bg-gray-50'
                                                    }`}
                                            >
                                                <div className="flex items-center gap-4">
                                                    {func.tem_divergencia ? (
                                                        <div className="relative">
                                                            <div className="bg-red-100 p-2 rounded-full">
                                                                <XCircle className="text-red-600" size={20} />
                                                            </div>
                                                            {errosCount > 0 && (
                                                                <span className="absolute -top-1 -right-1 bg-red-600 text-white text-[10px] rounded-full w-5 h-5 flex items-center justify-center font-bold shadow-sm ring-2 ring-white">
                                                                    {errosCount}
                                                                </span>
                                                            )}
                                                        </div>
                                                    ) : (
                                                        <div className="bg-green-100 p-2 rounded-full">
                                                            <CheckCircle className="text-green-600" size={20} />
                                                        </div>
                                                    )}

                                                    <div>
                                                        <div className="flex items-center gap-3">
                                                            <p className="font-bold text-gray-800 text-base">{func.nome}</p>
                                                            {func.cargo && func.cargo.toLowerCase().includes('aprendiz') && (
                                                                <span className="bg-purple-100 text-purple-700 text-xs px-2.5 py-0.5 rounded-full font-bold border border-purple-200">
                                                                    Jovem Aprendiz
                                                                </span>
                                                            )}
                                                        </div>
                                                        <p className="text-xs text-gray-500 mt-0.5 font-mono">
                                                            Matrícula: {func.matricula} • {func.itens.length} eventos analisados
                                                        </p>
                                                    </div>
                                                </div>

                                                <div className="flex items-center gap-3">
                                                    <span className={`text-sm font-medium px-3 py-1 rounded-full ${func.tem_divergencia ? 'text-red-700 bg-red-100' : 'text-green-700 bg-green-100'
                                                        }`}>
                                                        {func.tem_divergencia ? 'Pendência' : 'Conforme'}
                                                    </span>
                                                    <div className="text-gray-400 p-1 rounded-full hover:bg-gray-200 transition-colors">
                                                        {expandedRows[func.matricula] ? <ChevronUp size={20} /> : <ChevronDown size={20} />}
                                                    </div>
                                                </div>
                                            </div>

                                            {/* Tabela de Detalhes (Expandida) */}
                                            {expandedRows[func.matricula] && (
                                                <div className="bg-slate-50 p-6 border-t border-gray-200 shadow-inner">
                                                    <div className="overflow-hidden rounded-lg border border-gray-200 shadow-sm bg-white">
                                                        <table className="w-full text-sm">
                                                            <thead className="text-xs text-gray-500 uppercase bg-gray-100 border-b border-gray-200">
                                                                <tr>
                                                                    <th className="px-6 py-3 text-left font-semibold">Evento</th>
                                                                    <th className="px-6 py-3 text-right font-semibold">Base Calc.</th>
                                                                    <th className="px-6 py-3 text-right font-semibold">Esperado (Calc)</th>
                                                                    <th className="px-6 py-3 text-right font-semibold">Real (Folha)</th>
                                                                    <th className="px-6 py-3 text-center font-semibold">Status</th>
                                                                    <th className="px-6 py-3 text-right font-semibold">Diferença</th>
                                                                    <th className="px-6 py-3 text-center font-semibold">Memória</th>
                                                                </tr>
                                                            </thead>
                                                            <tbody className="divide-y divide-gray-100">
                                                                {func.itens.map((item, idx) => (
                                                                    <tr key={idx} className={`transition-colors hover:bg-gray-50 ${item.status === "ERRO" ? 'bg-red-50/50' : ''}`}>
                                                                        <td className="px-6 py-3">
                                                                            <div className="flex flex-col">
                                                                                <span className="font-semibold text-gray-700">{item.evento}</span>
                                                                                {item.codigo && (
                                                                                    <span className="text-[10px] text-gray-400 font-mono flex items-center gap-1 mt-0.5">
                                                                                        <Hash size={10} /> {item.codigo}
                                                                                    </span>
                                                                                )}
                                                                            </div>
                                                                        </td>
                                                                        <td className="px-6 py-3 text-right text-gray-500 font-mono text-xs">
                                                                            {item.base > 0 ? formatMoney(item.base) : '-'}
                                                                        </td>
                                                                        <td className="px-6 py-3 text-right text-blue-600 font-mono font-bold bg-blue-50/30">
                                                                            {formatMoney(item.esperado)}
                                                                        </td>
                                                                        <td className="px-6 py-3 text-right text-gray-700 font-mono font-medium">
                                                                            {formatMoney(item.real)}
                                                                        </td>
                                                                        <td className="px-6 py-3 text-center">
                                                                            {item.status === "OK" ? (
                                                                                <span className="inline-flex items-center gap-1 bg-green-100 text-green-700 text-[10px] px-2 py-0.5 rounded-full font-bold uppercase tracking-wider border border-green-200">
                                                                                    <CheckCircle size={10} /> OK
                                                                                </span>
                                                                            ) : (
                                                                                <span className="inline-flex items-center gap-1 bg-red-100 text-red-700 text-[10px] px-2 py-0.5 rounded-full font-bold uppercase tracking-wider border border-red-200">
                                                                                    <AlertTriangle size={10} /> ERRO
                                                                                </span>
                                                                            )}
                                                                        </td>
                                                                        <td className={`px-6 py-3 text-right font-mono font-bold ${item.status === "ERRO" ? 'text-red-600' : 'text-gray-300'}`}>
                                                                            {item.diferenca !== 0 ? (item.diferenca > 0 ? `+${formatMoney(item.diferenca)}` : formatMoney(item.diferenca)) : '-'}
                                                                        </td>
                                                                        <td className="px-6 py-3 text-center">
                                                                            {item.formula && (
                                                                                <div className="group/tooltip relative inline-flex justify-center">
                                                                                    <HelpCircle size={18} className="text-gray-400 hover:text-blue-500 cursor-help transition-colors" />
                                                                                    <div className="absolute bottom-full mb-2 right-1/2 translate-x-1/2 w-72 bg-gray-800 text-white text-xs rounded-lg shadow-xl opacity-0 group-hover/tooltip:opacity-100 transition-all duration-200 z-50 p-3 pointer-events-none transform scale-95 group-hover/tooltip:scale-100">
                                                                                        <div className="font-bold border-b border-gray-600 pb-1.5 mb-1.5 text-gray-300 flex justify-between">
                                                                                            <span>Fórmula Aplicada</span>
                                                                                            <Calculator size={12} />
                                                                                        </div>
                                                                                        <div className="font-mono text-yellow-300 text-center text-[11px] leading-relaxed break-words">
                                                                                            {item.formula}
                                                                                        </div>
                                                                                        {/* Seta do tooltip */}
                                                                                        <div className="absolute top-full left-1/2 -translate-x-1/2 border-4 border-transparent border-t-gray-800"></div>
                                                                                    </div>
                                                                                </div>
                                                                            )}
                                                                        </td>
                                                                    </tr>
                                                                ))}
                                                            </tbody>
                                                        </table>
                                                    </div>
                                                </div>
                                            )}
                                        </div>
                                    );
                                })}
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
        <div className="bg-white p-6 rounded-xl shadow-sm border border-gray-100 flex items-center gap-4 hover:shadow-md transition-shadow group">
            <div className={`p-4 rounded-full ${bgIcon} group-hover:scale-110 transition-transform`}>{icon}</div>
            <div>
                <p className="text-xs text-gray-500 uppercase tracking-wide font-semibold mb-1">{title}</p>
                <p className={`text-3xl font-extrabold ${color}`}>{value}</p>
            </div>
        </div>
    );
}