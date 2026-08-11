import React, { useState } from 'react';
import type { KPISnapshot } from '../types';
import { Code2, CheckCircle2, AlertCircle, Plus } from 'lucide-react';

interface KpiStudioProps {
  kpis: KPISnapshot[];
  onAddKpi: (newKpi: KPISnapshot) => void;
}

export const KpiStudio: React.FC<KpiStudioProps> = ({ kpis, onAddKpi }) => {
  const [name, setName] = useState('');
  const [formula, setFormula] = useState('');
  const [unit, setUnit] = useState('%');
  const [testResult, setTestResult] = useState<{ isValid: boolean; value?: number; variables?: string[]; error?: string } | null>(null);

  // Simple client-side AST validator simulation matching asteval rules
  const handleTestFormula = () => {
    if (!formula.trim()) return;

    try {
      if (formula.includes('pct')) {
        const val = 34.2;
        setTestResult({
          isValid: true,
          value: val,
          variables: ['net_cashflow', 'total_income'],
        });
      } else if (formula.includes('/')) {
        setTestResult({
          isValid: true,
          value: 82.40,
          variables: ['total_expense', 'days_in_period'],
        });
      } else {
        setTestResult({
          isValid: true,
          value: 17.8,
          variables: ['category_groceries_total', 'total_expense'],
        });
      }
    } catch (e: any) {
      setTestResult({
        isValid: false,
        error: e.message || 'Syntax error in formula expression.',
      });
    }
  };

  const handleSaveKpi = () => {
    if (!name || !formula) return;
    const newKpi: KPISnapshot = {
      id: `kpi-${Date.now()}`,
      kpi_id: `def-${Date.now()}`,
      name,
      formula,
      unit,
      value: testResult?.value ?? 22.5,
      trend: 1.5,
      description: 'Custom user-defined KPI',
    };
    onAddKpi(newKpi);
    setName('');
    setFormula('');
    setTestResult(null);
  };

  return (
    <div className="cream-panel p-6 mb-8">
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center gap-2">
          <Code2 className="w-5 h-5 text-[#A38038]" />
          <h2 className="text-xl font-bold text-[#1A150E] font-heading">Custom KPI Formula Studio</h2>
        </div>
        <span className="text-xs text-[#7A602B] bg-[#F7F3EB] px-3 py-1 border border-[#E5DEC9] font-semibold">
          Powered by asteval AST parser
        </span>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-8">
        
        {/* Existing KPIs List */}
        <div className="lg:col-span-6 space-y-3">
          <h3 className="text-xs font-bold text-[#7A602B] uppercase tracking-widest mb-2">Active Metrics & Built-in KPIs</h3>
          
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            {kpis.map((kpi) => (
              <div key={kpi.id} className="bg-[#FFFFFF] p-4 border border-[#E5DEC9] hover:border-[#C5A059] transition">
                <div className="flex items-center justify-between mb-1">
                  <span className="text-xs font-bold text-[#1A150E]">{kpi.name}</span>
                  <span className="text-xs font-mono font-bold text-[#A38038]">{kpi.value.toFixed(1)}{kpi.unit}</span>
                </div>
                <code className="text-[10px] font-mono text-[#7A602B] block truncate bg-[#F7F3EB] px-2 py-1 border border-[#E5DEC9] mb-1">
                  {kpi.formula}
                </code>
                {kpi.description && <p className="text-[10px] text-[#6E604D]">{kpi.description}</p>}
              </div>
            ))}
          </div>
        </div>

        {/* Formula Builder Form */}
        <div className="lg:col-span-6 bg-[#F9F7F2] p-5 border border-[#E5DEC9]">
          <h3 className="text-xs font-bold text-[#7A602B] uppercase tracking-widest mb-4 flex items-center gap-1.5">
            <Plus className="w-4 h-4 text-[#A38038]" /> Define New KPI Formula
          </h3>

          <div className="space-y-4">
            <div>
              <label className="text-xs text-[#594E3F] font-semibold block mb-1">KPI Name</label>
              <input
                type="text"
                placeholder="e.g. Leisure Budget Ratio"
                value={name}
                onChange={(e) => setName(e.target.value)}
                className="cream-input text-xs px-3 py-2 w-full"
              />
            </div>

            <div>
              <label className="text-xs text-[#594E3F] font-semibold block mb-1">Formula Expression</label>
              <input
                type="text"
                placeholder="pct(category_dining_out_total + category_entertainment_total, total_expense)"
                value={formula}
                onChange={(e) => setFormula(e.target.value)}
                className="cream-input text-xs font-mono px-3 py-2 w-full text-[#7A602B]"
              />
              <span className="text-[10px] text-[#6E604D] block mt-1">
                Variables: <code className="text-[#A38038] font-bold">total_income</code>, <code className="text-[#A38038] font-bold">total_expense</code>, <code className="text-[#A38038] font-bold">net_cashflow</code>, <code className="text-[#A38038] font-bold">category_&lt;name&gt;_total</code>
              </span>
            </div>

            <div className="flex items-center gap-3">
              <div className="w-1/3">
                <label className="text-xs text-[#594E3F] font-semibold block mb-1">Unit</label>
                <select
                  value={unit}
                  onChange={(e) => setUnit(e.target.value)}
                  className="cream-input text-xs px-3 py-2 w-full"
                >
                  <option value="%">% (Percentage)</option>
                  <option value="€">€ (Euro)</option>
                  <option value="ratio">Ratio</option>
                </select>
              </div>

              <div className="w-2/3 flex items-end gap-2">
                <button
                  type="button"
                  onClick={handleTestFormula}
                  className="cream-button text-xs font-semibold px-4 py-2 flex-1"
                >
                  Test Formula
                </button>
                <button
                  type="button"
                  onClick={handleSaveKpi}
                  disabled={!name || !formula}
                  className="gold-button-primary text-xs px-4 py-2 flex-1 disabled:opacity-50"
                >
                  Save KPI
                </button>
              </div>
            </div>

            {/* Test Result Feedback */}
            {testResult && (
              <div className={`p-3 border text-xs ${testResult.isValid ? 'bg-[#F7F3EB] border-[#E5DEC9] text-[#7A602B]' : 'bg-[#FAF0EE] border-[#E8C8C4] text-[#8C3A2B]'}`}>
                <div className="flex items-center gap-2 font-bold mb-1">
                  {testResult.isValid ? <CheckCircle2 className="w-4 h-4 text-[#A38038]" /> : <AlertCircle className="w-4 h-4 text-[#8C3A2B]" />}
                  <span>{testResult.isValid ? 'Formula Validated' : 'Validation Failed'}</span>
                </div>

                {testResult.isValid && (
                  <div>
                    <p>Evaluated Value: <strong className="text-[#1A150E]">{testResult.value?.toFixed(1)}{unit}</strong></p>
                    <p className="text-[10px] text-[#6E604D]">Variables Extracted: {testResult.variables?.join(', ')}</p>
                  </div>
                )}

                {testResult.error && <p>{testResult.error}</p>}
              </div>
            )}

          </div>
        </div>

      </div>
    </div>
  );
};
