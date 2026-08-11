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
    <div className="cream-panel p-6 mb-8 relative overflow-hidden">
      <div className="ambient-glow-gold -top-32 -right-32" />

      <div className="flex flex-col md:flex-row items-start md:items-center justify-between gap-4 mb-6">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <Sparkles className="w-5 h-5 text-[#A38038]" />
            <h2 className="text-xl font-bold text-[#1A150E] font-heading">Interactive Savings Growth & Scenario Simulator</h2>
          </div>
          <p className="text-xs text-[#6E604D]">
            Project long-term compound growth using benchmark returns (MSCI World default 7%) and see instant impact of savings rate shifts.
          </p>
        </div>

        <div className="flex items-center gap-2 px-3 py-1.5 bg-[#F7F3EB] border border-[#E5DEC9] text-[#7A602B] text-xs font-semibold uppercase tracking-wider">
          <ShieldCheck className="w-4 h-4 text-[#A38038]" />
          <span>MSCI World Benchmark (7.0%)</span>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-8">
        
        {/* Sliders Column */}
        <div className="lg:col-span-5 space-y-5 bg-[#F9F7F2] p-5 border border-[#E5DEC9]">
          <div className="flex items-center gap-2 text-xs font-bold text-[#7A602B] uppercase tracking-widest mb-2">
            <Sliders className="w-4 h-4 text-[#A38038]" /> Simulator Controls
          </div>

          {/* Monthly Savings */}
          <div>
            <div className="flex justify-between text-xs mb-1">
              <span className="text-[#594E3F] font-medium">Monthly Savings Contribution</span>
              <span className="font-bold text-[#A38038]">€{monthlySavings.toLocaleString()} / mo</span>
            </div>
            <input
              type="range"
              min="100"
              max="4000"
              step="50"
              value={monthlySavings}
              onChange={(e) => setMonthlySavings(Number(e.target.value))}
              className="w-full accent-[#A38038] bg-[#E5DEC9] cursor-pointer"
            />
          </div>

          {/* Expected Return */}
          <div>
            <div className="flex justify-between text-xs mb-1">
              <span className="text-[#594E3F] font-medium">Expected Annual Return</span>
              <span className="font-bold text-[#1A150E]">{annualReturn.toFixed(1)}% / yr</span>
            </div>
            <input
              type="range"
              min="2.0"
              max="12.0"
              step="0.5"
              value={annualReturn}
              onChange={(e) => setAnnualReturn(Number(e.target.value))}
              className="w-full accent-[#1A150E] bg-[#E5DEC9] cursor-pointer"
            />
          </div>

          {/* Investment Horizon */}
          <div>
            <div className="flex justify-between text-xs mb-1">
              <span className="text-[#594E3F] font-medium">Investment Horizon</span>
              <span className="font-bold text-[#A38038]">{horizonYears} Years</span>
            </div>
            <input
              type="range"
              min="5"
              max="35"
              step="1"
              value={horizonYears}
              onChange={(e) => setHorizonYears(Number(e.target.value))}
              className="w-full accent-[#A38038] bg-[#E5DEC9] cursor-pointer"
            />
          </div>

          {/* Inflation */}
          <div>
            <div className="flex justify-between text-xs mb-1">
              <span className="text-[#594E3F] font-medium">Expected Inflation</span>
              <span className="font-bold text-[#594E3F]">{inflation.toFixed(1)}% / yr</span>
            </div>
            <input
              type="range"
              min="0.5"
              max="5.0"
              step="0.5"
              value={inflation}
              onChange={(e) => setInflation(Number(e.target.value))}
              className="w-full accent-[#594E3F] bg-[#E5DEC9] cursor-pointer"
            />
          </div>
        </div>

        {/* Chart & Results Column */}
        <div className="lg:col-span-7 flex flex-col justify-between">
          
          {/* Big Summary Cards */}
          <div className="grid grid-cols-2 sm:grid-cols-3 gap-4 mb-5">
            <div className="bg-[#FFFFFF] border border-[#E5DEC9] p-4">
              <span className="text-xs text-[#7A602B] font-semibold block mb-1">Nominal Portfolio</span>
              <span className="text-2xl font-extrabold text-[#1A150E] font-heading">€{Math.round(baselineNominal).toLocaleString()}</span>
              <span className="text-[10px] text-[#6E604D] block mt-0.5">Today's cash growth</span>
            </div>

            <div className="bg-[#FFFFFF] border border-[#E5DEC9] p-4">
              <span className="text-xs text-[#7A602B] font-semibold block mb-1">Real (Inflation-Adj.)</span>
              <span className="text-2xl font-extrabold text-[#A38038] font-heading">€{Math.round(baselineReal).toLocaleString()}</span>
              <span className="text-[10px] text-[#6E604D] block mt-0.5">Purchasing power in {horizonYears}y</span>
            </div>

            <div className="bg-[#FFFFFF] border border-[#E5DEC9] p-4 col-span-2 sm:col-span-1">
              <span className="text-xs text-[#1A150E] font-semibold block mb-1">Compound Interest</span>
              <span className="text-2xl font-extrabold text-[#1A150E] font-heading">€{Math.round(totalGrowthNominal).toLocaleString()}</span>
              <span className="text-[10px] text-[#6E604D] block mt-0.5">Pure market returns</span>
            </div>
          </div>

          {/* SVG Growth Chart */}
          <div className="bg-[#F9F7F2] p-4 border border-[#E5DEC9] mb-5 relative">
            <div className="flex items-center justify-between text-xs text-[#594E3F] mb-2 font-medium">
              <div className="flex items-center gap-4">
                <span className="flex items-center gap-1.5"><span className="w-2.5 h-2.5 bg-[#C5A059]" /> Nominal</span>
                <span className="flex items-center gap-1.5"><span className="w-2.5 h-2.5 bg-[#1A150E]" /> Real (Inflation-Adj.)</span>
              </div>
              <span className="font-bold text-[#A38038]">{horizonYears} Years</span>
            </div>

            <svg viewBox={`0 0 ${svgWidth} ${svgHeight}`} className="w-full h-36 overflow-visible">
              {/* Grid lines */}
              <line x1="0" y1="40" x2={svgWidth} y2="40" stroke="rgba(197, 160, 89, 0.15)" strokeDasharray="4" />
              <line x1="0" y1="100" x2={svgWidth} y2="100" stroke="rgba(197, 160, 89, 0.15)" strokeDasharray="4" />
              <line x1="0" y1="160" x2={svgWidth} y2="160" stroke="rgba(197, 160, 89, 0.15)" strokeDasharray="4" />

              {/* Real path */}
              <path d={realPath} fill="none" stroke="#1A150E" strokeWidth="2.5" strokeDasharray="3 3" />

              {/* Nominal path */}
              <path d={nominalPath} fill="none" stroke="#C5A059" strokeWidth="3" />
            </svg>
          </div>

          {/* Scenario Cards */}
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
            <div className="cream-panel p-3 border border-[#E5DEC9]">
              <span className="text-[11px] font-semibold text-[#594E3F] block mb-0.5">+5% Savings Rate</span>
              <span className="text-sm font-bold text-[#A38038] font-heading">€{Math.round(sc5pctReal).toLocaleString()}</span>
              <span className="text-[10px] text-[#2D6A4F] font-semibold block mt-0.5">+€{Math.round(sc5pctReal - baselineReal).toLocaleString()} extra</span>
            </div>

            <div className="cream-panel p-3 border border-[#E5DEC9]">
              <span className="text-[11px] font-semibold text-[#594E3F] block mb-0.5">+10% Savings Rate</span>
              <span className="text-sm font-bold text-[#A38038] font-heading">€{Math.round(sc10pctReal).toLocaleString()}</span>
              <span className="text-[10px] text-[#2D6A4F] font-semibold block mt-0.5">+€{Math.round(sc10pctReal - baselineReal).toLocaleString()} extra</span>
            </div>

            <div className="cream-panel p-3 border border-[#E5DEC9]">
              <span className="text-[11px] font-semibold text-[#594E3F] block mb-0.5">Double Savings</span>
              <span className="text-sm font-bold text-[#1A150E] font-heading">€{Math.round(scDoubleReal).toLocaleString()}</span>
              <span className="text-[10px] text-[#2D6A4F] font-semibold block mt-0.5">+€{Math.round(scDoubleReal - baselineReal).toLocaleString()} extra</span>
            </div>
          </div>

        </div>

      </div>
    </div>
  );
};
