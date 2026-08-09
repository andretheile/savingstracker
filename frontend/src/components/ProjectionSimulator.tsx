import React, { useState } from 'react';
import { Sparkles, Sliders, ShieldCheck } from 'lucide-react';

export const ProjectionSimulator: React.FC = () => {
  const [currentBalance] = useState<number>(19510);
  const [monthlyIncome] = useState<number>(3850);
  const [monthlySavings, setMonthlySavings] = useState<number>(1315);
  const [annualReturn, setAnnualReturn] = useState<number>(7.0);
  const [inflation, setInflation] = useState<number>(2.0);
  const [horizonYears, setHorizonYears] = useState<number>(20);

  // Math helper
  const calcFutureValue = (P: number, C: number, rAnnual: number, years: number) => {
    const r = rAnnual / 100 / 12;
    const n = years * 12;
    if (r === 0) return P + C * n;
    return P * Math.pow(1 + r, n) + C * (Math.pow(1 + r, n) - 1) / r;
  };

  const realReturnAnnual = ((1 + annualReturn / 100) / (1 + inflation / 100) - 1) * 100;

  const baselineNominal = calcFutureValue(currentBalance, monthlySavings, annualReturn, horizonYears);
  const baselineReal = calcFutureValue(currentBalance, monthlySavings, realReturnAnnual, horizonYears);
  const totalContributed = currentBalance + monthlySavings * horizonYears * 12;
  const totalGrowthNominal = baselineNominal - totalContributed;

  // What-if scenarios
  const sc5pctMonthly = monthlySavings + (monthlyIncome * 0.05);
  const sc5pctReal = calcFutureValue(currentBalance, sc5pctMonthly, realReturnAnnual, horizonYears);

  const sc10pctMonthly = monthlySavings + (monthlyIncome * 0.10);
  const sc10pctReal = calcFutureValue(currentBalance, sc10pctMonthly, realReturnAnnual, horizonYears);

  const scDoubleMonthly = monthlySavings * 2;
  const scDoubleReal = calcFutureValue(currentBalance, scDoubleMonthly, realReturnAnnual, horizonYears);

  // Generate chart data points
  const points: { year: number; nominal: number; real: number }[] = [];
  const step = Math.max(1, Math.floor(horizonYears / 10));
  for (let y = 0; y <= horizonYears; y += step) {
    points.push({
      year: y,
      nominal: calcFutureValue(currentBalance, monthlySavings, annualReturn, y),
      real: calcFutureValue(currentBalance, monthlySavings, realReturnAnnual, y),
    });
  }

  // SVG Chart path calculation
  const maxVal = Math.max(...points.map(p => p.nominal), 1000);
  const svgWidth = 500;
  const svgHeight = 180;

  const getX = (i: number) => (i / (points.length - 1)) * svgWidth;
  const getY = (val: number) => svgHeight - (val / maxVal) * (svgHeight - 20) - 10;

  const nominalPath = points.reduce((acc, p, i) => `${acc} ${i === 0 ? 'M' : 'L'} ${getX(i)} ${getY(p.nominal)}`, '');
  const realPath = points.reduce((acc, p, i) => `${acc} ${i === 0 ? 'M' : 'L'} ${getX(i)} ${getY(p.real)}`, '');

  return (
    <div className="glass-panel p-6 rounded-3xl mb-8 relative overflow-hidden">
      <div className="ambient-glow-purple -top-32 -right-32" />

      <div className="flex flex-col md:flex-row items-start md:items-center justify-between gap-4 mb-6">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <Sparkles className="w-5 h-5 text-cyan-400" />
            <h2 className="text-xl font-bold text-white font-heading">Interactive Savings Growth & Scenario Simulator</h2>
          </div>
          <p className="text-xs text-slate-400">
            Project long-term compound growth using benchmark returns (MSCI World default 7%) and see instant impact of savings rate shifts.
          </p>
        </div>

        <div className="flex items-center gap-2 px-3 py-1.5 rounded-xl bg-cyan-500/10 border border-cyan-500/20 text-cyan-300 text-xs font-semibold">
          <ShieldCheck className="w-4 h-4 text-cyan-400" />
          <span>MSCI World Benchmark (7.0%)</span>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-8">
        
        {/* Sliders Column */}
        <div className="lg:col-span-5 space-y-5 bg-slate-900/40 p-5 rounded-2xl border border-slate-800/80">
          <div className="flex items-center gap-2 text-xs font-semibold text-cyan-400 uppercase tracking-wider mb-2">
            <Sliders className="w-4 h-4" /> Simulator Controls
          </div>

          {/* Monthly Savings */}
          <div>
            <div className="flex justify-between text-xs mb-1">
              <span className="text-slate-300">Monthly Savings Contribution</span>
              <span className="font-semibold text-cyan-400">€{monthlySavings.toLocaleString()} / mo</span>
            </div>
            <input
              type="range"
              min="100"
              max="4000"
              step="50"
              value={monthlySavings}
              onChange={(e) => setMonthlySavings(Number(e.target.value))}
              className="w-full accent-cyan-400 bg-slate-800 rounded-lg cursor-pointer"
            />
          </div>

          {/* Expected Return */}
          <div>
            <div className="flex justify-between text-xs mb-1">
              <span className="text-slate-300">Expected Annual Return</span>
              <span className="font-semibold text-indigo-400">{annualReturn.toFixed(1)}% / yr</span>
            </div>
            <input
              type="range"
              min="2.0"
              max="12.0"
              step="0.5"
              value={annualReturn}
              onChange={(e) => setAnnualReturn(Number(e.target.value))}
              className="w-full accent-indigo-400 bg-slate-800 rounded-lg cursor-pointer"
            />
          </div>

          {/* Investment Horizon */}
          <div>
            <div className="flex justify-between text-xs mb-1">
              <span className="text-slate-300">Investment Horizon</span>
              <span className="font-semibold text-emerald-400">{horizonYears} Years</span>
            </div>
            <input
              type="range"
              min="5"
              max="35"
              step="1"
              value={horizonYears}
              onChange={(e) => setHorizonYears(Number(e.target.value))}
              className="w-full accent-emerald-400 bg-slate-800 rounded-lg cursor-pointer"
            />
          </div>

          {/* Inflation */}
          <div>
            <div className="flex justify-between text-xs mb-1">
              <span className="text-slate-300">Expected Inflation</span>
              <span className="font-semibold text-rose-400">{inflation.toFixed(1)}% / yr</span>
            </div>
            <input
              type="range"
              min="0.5"
              max="5.0"
              step="0.5"
              value={inflation}
              onChange={(e) => setInflation(Number(e.target.value))}
              className="w-full accent-rose-400 bg-slate-800 rounded-lg cursor-pointer"
            />
          </div>
        </div>

        {/* Chart & Results Column */}
        <div className="lg:col-span-7 flex flex-col justify-between">
          
          {/* Big Summary Cards */}
          <div className="grid grid-cols-2 sm:grid-cols-3 gap-4 mb-5">
            <div className="bg-cyan-500/10 border border-cyan-500/20 p-4 rounded-2xl">
              <span className="text-xs text-cyan-300 block mb-1">Nominal Portfolio</span>
              <span className="text-2xl font-extrabold text-white font-heading">€{Math.round(baselineNominal).toLocaleString()}</span>
              <span className="text-[10px] text-cyan-400/80 block mt-0.5">Today's cash growth</span>
            </div>

            <div className="bg-emerald-500/10 border border-emerald-500/20 p-4 rounded-2xl">
              <span className="text-xs text-emerald-300 block mb-1">Real (Inflation-Adj.)</span>
              <span className="text-2xl font-extrabold text-emerald-300 font-heading">€{Math.round(baselineReal).toLocaleString()}</span>
              <span className="text-[10px] text-emerald-400/80 block mt-0.5">Purchasing power in {horizonYears}y</span>
            </div>

            <div className="bg-purple-500/10 border border-purple-500/20 p-4 rounded-2xl col-span-2 sm:col-span-1">
              <span className="text-xs text-purple-300 block mb-1">Compound Interest</span>
              <span className="text-2xl font-extrabold text-purple-300 font-heading">€{Math.round(totalGrowthNominal).toLocaleString()}</span>
              <span className="text-[10px] text-purple-400/80 block mt-0.5">Pure market returns</span>
            </div>
          </div>

          {/* SVG Growth Chart */}
          <div className="bg-slate-900/60 p-4 rounded-2xl border border-slate-800 mb-5 relative">
            <div className="flex items-center justify-between text-xs text-slate-400 mb-2">
              <div className="flex items-center gap-4">
                <span className="flex items-center gap-1.5"><span className="w-2.5 h-2.5 rounded-full bg-cyan-400" /> Nominal</span>
                <span className="flex items-center gap-1.5"><span className="w-2.5 h-2.5 rounded-full bg-emerald-400" /> Real (Inflation-Adj.)</span>
              </div>
              <span>{horizonYears} Years</span>
            </div>

            <svg viewBox={`0 0 ${svgWidth} ${svgHeight}`} className="w-full h-36 overflow-visible">
              {/* Grid lines */}
              <line x1="0" y1="40" x2={svgWidth} y2="40" stroke="rgba(255,255,255,0.05)" strokeDasharray="4" />
              <line x1="0" y1="100" x2={svgWidth} y2="100" stroke="rgba(255,255,255,0.05)" strokeDasharray="4" />
              <line x1="0" y1="160" x2={svgWidth} y2="160" stroke="rgba(255,255,255,0.05)" strokeDasharray="4" />

              {/* Real path */}
              <path d={realPath} fill="none" stroke="#10b981" strokeWidth="2.5" strokeDasharray="3 3" />

              {/* Nominal path */}
              <path d={nominalPath} fill="none" stroke="#06b6d4" strokeWidth="3" />
            </svg>
          </div>

          {/* Scenario Cards */}
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
            <div className="glass-panel p-3 rounded-xl border-l-4 border-l-cyan-400">
              <span className="text-[11px] font-semibold text-slate-300 block mb-0.5">+5% Savings Rate</span>
              <span className="text-sm font-bold text-cyan-300 font-heading">€{Math.round(sc5pctReal).toLocaleString()}</span>
              <span className="text-[10px] text-emerald-400 block mt-0.5">+€{Math.round(sc5pctReal - baselineReal).toLocaleString()} extra</span>
            </div>

            <div className="glass-panel p-3 rounded-xl border-l-4 border-l-indigo-400">
              <span className="text-[11px] font-semibold text-slate-300 block mb-0.5">+10% Savings Rate</span>
              <span className="text-sm font-bold text-indigo-300 font-heading">€{Math.round(sc10pctReal).toLocaleString()}</span>
              <span className="text-[10px] text-emerald-400 block mt-0.5">+€{Math.round(sc10pctReal - baselineReal).toLocaleString()} extra</span>
            </div>

            <div className="glass-panel p-3 rounded-xl border-l-4 border-l-purple-400">
              <span className="text-[11px] font-semibold text-slate-300 block mb-0.5">Double Savings</span>
              <span className="text-sm font-bold text-purple-300 font-heading">€{Math.round(scDoubleReal).toLocaleString()}</span>
              <span className="text-[10px] text-emerald-400 block mt-0.5">+€{Math.round(scDoubleReal - baselineReal).toLocaleString()} extra</span>
            </div>
          </div>

        </div>

      </div>
    </div>
  );
};
