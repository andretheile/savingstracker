import React, { useEffect, useRef, useState } from 'react';
import type { KPISnapshot } from '../types';
import { CheckCircle2, AlertCircle, Plus } from 'lucide-react';
import { SelectMenu } from './SelectMenu';
import { fetchJson } from '../api';

interface KpiStudioProps {
  userId: string;
  kpis: KPISnapshot[];
  onAddKpi: (newKpi: KPISnapshot) => void | Promise<void>;
  focusNew?: number;
}

export const KpiStudio: React.FC<KpiStudioProps> = ({ userId, kpis, onAddKpi, focusNew = 0 }) => {
  const [name, setName] = useState('');
  const [formula, setFormula] = useState('');
  const [unit, setUnit] = useState('%');
  const [testResult, setTestResult] = useState<{ isValid: boolean; value?: number; variables?: string[]; error?: string } | null>(null);
  const nameRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (focusNew > 0) {
      nameRef.current?.focus();
    }
  }, [focusNew]);

  const handleTestFormula = async () => {
    if (!formula.trim()) return;

    try {
      const result = await fetchJson<{ is_valid: boolean; variables: string[]; errors: string[] }>(
        '/kpis/validate',
        { method: 'POST', body: JSON.stringify({ formula }) }
      );
      if (result.is_valid) {
        setTestResult({
          isValid: true,
          variables: result.variables,
        });
      } else {
        setTestResult({
          isValid: false,
          error: result.errors.join(', ') || 'Invalid formula',
        });
      }
    } catch (e: unknown) {
      setTestResult({
        isValid: false,
        error: e instanceof Error ? e.message : 'Could not validate formula.',
      });
    }
  };

  const handleSaveKpi = async () => {
    if (!name || !formula) return;
    await onAddKpi({
      id: `kpi-${Date.now()}`,
      kpi_id: userId,
      name,
      formula,
      unit,
      value: 0,
      description: 'Custom user-defined KPI',
    });
    setName('');
    setFormula('');
    setTestResult(null);
  };

  return (
    <div className="cream-panel p-6 mb-8">
      <div className="mb-6">
        <h2 className="text-lg font-semibold text-[#1A1714] font-heading">KPIs</h2>
        <p className="text-xs text-[#6B645A] mt-0.5">Define custom metrics from income, expense, and category totals.</p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-8">
        <div className="lg:col-span-6 space-y-3">
          <h3 className="text-[11px] font-medium text-[#8A8278] uppercase tracking-wide mb-2">Active metrics</h3>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            {kpis.map((kpi) => (
              <div key={kpi.id} className="bg-[#FFFFFF] p-4 border border-[#E5DFD4]">
                <div className="flex items-center justify-between mb-1.5">
                  <span className="text-xs font-medium text-[#1A1714]">{kpi.name}</span>
                  <span className="text-xs font-medium tabular-nums text-[#1A1714]">
                    {kpi.unit === '€' ? `€${kpi.value.toFixed(2)}` : `${kpi.value.toFixed(1)}${kpi.unit}`}
                  </span>
                </div>
                <code className="text-[10px] font-mono text-[#6B645A] block truncate bg-[#F3F0EA] px-2 py-1 border border-[#E5DFD4] mb-1">
                  {kpi.formula}
                </code>
                {kpi.description && <p className="text-[10px] text-[#8A8278]">{kpi.description}</p>}
              </div>
            ))}
          </div>
        </div>

        <div className="lg:col-span-6 bg-[#F3F0EA] p-5 border border-[#E5DFD4]">
          <h3 className="text-[11px] font-medium text-[#8A8278] uppercase tracking-wide mb-4 flex items-center gap-1.5">
            <Plus className="w-3.5 h-3.5" strokeWidth={1.6} /> New formula
          </h3>

          <div className="space-y-4">
            <div>
              <label className="text-xs text-[#6B645A] font-medium block mb-1">Name</label>
              <input
                ref={nameRef}
                type="text"
                placeholder="e.g. Leisure budget ratio"
                value={name}
                onChange={(e) => setName(e.target.value)}
                className="cream-input text-xs px-3 py-2 w-full"
              />
            </div>

            <div>
              <label className="text-xs text-[#6B645A] font-medium block mb-1">Formula</label>
              <input
                type="text"
                placeholder="pct(category_dining_out_total + category_entertainment_total, total_expense)"
                value={formula}
                onChange={(e) => setFormula(e.target.value)}
                className="cream-input text-xs font-mono px-3 py-2 w-full"
              />
              <span className="text-[10px] text-[#8A8278] block mt-1.5">
                Variables: total_income, total_expense, net_cashflow, category_&lt;name&gt;_total
              </span>
            </div>

            <div className="grid grid-cols-3 gap-2 items-end">
              <div>
                <label className="text-xs text-[#6B645A] font-medium block mb-1">Unit</label>
                <SelectMenu
                  aria-label="Unit"
                  value={unit}
                  onChange={setUnit}
                  className="w-full"
                  options={[
                    { value: '%', label: '%' },
                    { value: '€', label: '€' },
                    { value: 'ratio', label: 'Ratio' },
                  ]}
                />
              </div>
              <button
                type="button"
                onClick={handleTestFormula}
                className="cream-button text-xs font-medium h-8 px-4"
              >
                Test
              </button>
              <button
                type="button"
                onClick={handleSaveKpi}
                disabled={!name || !formula}
                className="gold-button-primary text-xs h-8 px-4 disabled:opacity-50"
              >
                Save
              </button>
            </div>

            {testResult && (
              <div className={`p-3 border text-xs ${testResult.isValid ? 'bg-[#FFFFFF] border-[#E5DFD4] text-[#6B645A]' : 'bg-[#FAF4F2] border-[#E8D4CE] text-[#8C4A3A]'}`}>
                <div className="flex items-center gap-2 font-medium mb-1 text-[#1A1714]">
                  {testResult.isValid ? <CheckCircle2 className="w-3.5 h-3.5 text-[#3D6B54]" strokeWidth={1.6} /> : <AlertCircle className="w-3.5 h-3.5" strokeWidth={1.6} />}
                  <span>{testResult.isValid ? 'Valid' : 'Invalid'}</span>
                </div>

                {testResult.isValid && (
                  <div>
                    <p>Variables: <span className="text-[#1A1714] font-medium">{testResult.variables?.join(', ') || '—'}</span></p>
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
