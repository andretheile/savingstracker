import React, { useEffect, useState } from 'react';
import { SlidersHorizontal } from 'lucide-react';

interface ProjectionSimulatorProps {
  currentBalance: number;
  monthlyIncome: number;
  initialMonthlySavings: number;
}

export const ProjectionSimulator: React.FC<ProjectionSimulatorProps> = ({
  currentBalance,
  monthlyIncome,
  initialMonthlySavings,
}) => {
  const [monthlySavings, setMonthlySavings] = useState<number>(Math.max(0, initialMonthlySavings));
  const [annualReturn, setAnnualReturn] = useState<number>(7.0);
  const [inflation, setInflation] = useState<number>(2.0);
  const [horizonYears, setHorizonYears] = useState<number>(20);

  useEffect(() => {
    setMonthlySavings(Math.max(0, Math.round(initialMonthlySavings)));
  }, [initialMonthlySavings]);

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

  const sc5pctMonthly = monthlySavings + (monthlyIncome * 0.05);
  const sc5pctReal = calcFutureValue(currentBalance, sc5pctMonthly, realReturnAnnual, horizonYears);

  const sc10pctMonthly = monthlySavings + (monthlyIncome * 0.10);
  const sc10pctReal = calcFutureValue(currentBalance, sc10pctMonthly, realReturnAnnual, horizonYears);

  const scDoubleMonthly = monthlySavings * 2;
  const scDoubleReal = calcFutureValue(currentBalance, scDoubleMonthly, realReturnAnnual, horizonYears);

  const points: { year: number; nominal: number; real: number }[] = [];
  const step = Math.max(1, Math.floor(horizonYears / 10));
  for (let y = 0; y <= horizonYears; y += step) {
    points.push({
      year: y,
      nominal: calcFutureValue(currentBalance, monthlySavings, annualReturn, y),
      real: calcFutureValue(currentBalance, monthlySavings, realReturnAnnual, y),
    });
  }

  const maxVal = Math.max(...points.map(p => p.nominal), 1000);
  const svgWidth = 500;
  const svgHeight = 180;

  const getX = (i: number) => (i / (points.length - 1)) * svgWidth;
  const getY = (val: number) => svgHeight - (val / maxVal) * (svgHeight - 20) - 10;

  const nominalPath = points.reduce((acc, p, i) => `${acc} ${i === 0 ? 'M' : 'L'} ${getX(i)} ${getY(p.nominal)}`, '');
  const realPath = points.reduce((acc, p, i) => `${acc} ${i === 0 ? 'M' : 'L'} ${getX(i)} ${getY(p.real)}`, '');

  return (
    <div className="cream-panel p-6 mb-8">
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 mb-6">
        <div>
          <h2 className="text-lg font-semibold text-[#1A1714] font-heading">Projections</h2>
          <p className="text-xs text-[#6B645A] mt-0.5">
            Starting from your current €{Math.round(currentBalance).toLocaleString('de-DE')} across linked accounts. Default return is 7% (MSCI World).
          </p>
        </div>
        <span className="text-[11px] font-medium text-[#6B645A] px-2.5 py-1 bg-[#F3F0EA] border border-[#E5DFD4]">
          {horizonYears}-year horizon
        </span>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-8">
        <div className="lg:col-span-5 space-y-5 bg-[#F3F0EA] p-5 border border-[#E5DFD4]">
          <div className="flex items-center gap-2 text-[11px] font-medium text-[#8A8278] uppercase tracking-wide mb-1">
            <SlidersHorizontal className="w-3.5 h-3.5" strokeWidth={1.6} /> Assumptions
          </div>

          <div>
            <div className="flex justify-between text-xs mb-1.5">
              <span className="text-[#6B645A]">Monthly contribution</span>
              <span className="font-medium text-[#1A1714]">€{monthlySavings.toLocaleString()} / mo</span>
            </div>
            <input
              type="range"
              min="0"
              max={Math.max(4000, Math.round(monthlyIncome) || 4000)}
              step="50"
              value={monthlySavings}
              onChange={(e) => setMonthlySavings(Number(e.target.value))}
              className="w-full accent-[#1A1714] cursor-pointer"
            />
          </div>

          <div>
            <div className="flex justify-between text-xs mb-1.5">
              <span className="text-[#6B645A]">Expected annual return</span>
              <span className="font-medium text-[#1A1714]">{annualReturn.toFixed(1)}%</span>
            </div>
            <input
              type="range"
              min="2.0"
              max="12.0"
              step="0.5"
              value={annualReturn}
              onChange={(e) => setAnnualReturn(Number(e.target.value))}
              className="w-full accent-[#1A1714] cursor-pointer"
            />
          </div>

          <div>
            <div className="flex justify-between text-xs mb-1.5">
              <span className="text-[#6B645A]">Horizon</span>
              <span className="font-medium text-[#1A1714]">{horizonYears} years</span>
            </div>
            <input
              type="range"
              min="5"
              max="35"
              step="1"
              value={horizonYears}
              onChange={(e) => setHorizonYears(Number(e.target.value))}
              className="w-full accent-[#1A1714] cursor-pointer"
            />
          </div>

          <div>
            <div className="flex justify-between text-xs mb-1.5">
              <span className="text-[#6B645A]">Inflation</span>
              <span className="font-medium text-[#1A1714]">{inflation.toFixed(1)}%</span>
            </div>
            <input
              type="range"
              min="0.5"
              max="5.0"
              step="0.5"
              value={inflation}
              onChange={(e) => setInflation(Number(e.target.value))}
              className="w-full accent-[#1A1714] cursor-pointer"
            />
          </div>
        </div>

        <div className="lg:col-span-7 flex flex-col justify-between">
          <div className="grid grid-cols-2 sm:grid-cols-3 gap-3 mb-5">
            <div className="bg-[#FFFFFF] border border-[#E5DFD4] p-4">
              <span className="text-[11px] text-[#8A8278] font-medium block mb-1">Nominal</span>
              <span className="text-xl font-semibold text-[#1A1714] font-heading tracking-tight">€{Math.round(baselineNominal).toLocaleString()}</span>
              <span className="text-[10px] text-[#8A8278] block mt-1">Future value</span>
            </div>

            <div className="bg-[#FFFFFF] border border-[#E5DFD4] p-4">
              <span className="text-[11px] text-[#8A8278] font-medium block mb-1">Real</span>
              <span className="text-xl font-semibold text-[#1A1714] font-heading tracking-tight">€{Math.round(baselineReal).toLocaleString()}</span>
              <span className="text-[10px] text-[#8A8278] block mt-1">Inflation-adjusted</span>
            </div>

            <div className="bg-[#FFFFFF] border border-[#E5DFD4] p-4 col-span-2 sm:col-span-1">
              <span className="text-[11px] text-[#8A8278] font-medium block mb-1">Interest</span>
              <span className="text-xl font-semibold text-[#1A1714] font-heading tracking-tight">€{Math.round(totalGrowthNominal).toLocaleString()}</span>
              <span className="text-[10px] text-[#8A8278] block mt-1">Market returns</span>
            </div>
          </div>

          <div className="bg-[#F3F0EA] p-4 border border-[#E5DFD4] mb-5">
            <div className="flex items-center justify-between text-[11px] text-[#6B645A] mb-3">
              <div className="flex items-center gap-4">
                <span className="flex items-center gap-1.5"><span className="w-2 h-2 bg-[#8F7848]" /> Nominal</span>
                <span className="flex items-center gap-1.5"><span className="w-2 h-2 bg-[#1A1714]" /> Real</span>
              </div>
            </div>

            <svg viewBox={`0 0 ${svgWidth} ${svgHeight}`} className="w-full h-36 overflow-visible">
              <line x1="0" y1="40" x2={svgWidth} y2="40" stroke="rgba(26, 23, 20, 0.08)" />
              <line x1="0" y1="100" x2={svgWidth} y2="100" stroke="rgba(26, 23, 20, 0.08)" />
              <line x1="0" y1="160" x2={svgWidth} y2="160" stroke="rgba(26, 23, 20, 0.08)" />
              <path d={realPath} fill="none" stroke="#1A1714" strokeWidth="1.75" strokeDasharray="3 3" />
              <path d={nominalPath} fill="none" stroke="#8F7848" strokeWidth="1.75" />
            </svg>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
            <div className="border border-[#E5DFD4] p-3.5">
              <span className="text-[11px] text-[#8A8278] block mb-0.5">+5% savings rate</span>
              <span className="text-sm font-semibold text-[#1A1714] font-heading">€{Math.round(sc5pctReal).toLocaleString()}</span>
              <span className="text-[10px] text-[#3D6B54] block mt-0.5">+€{Math.round(sc5pctReal - baselineReal).toLocaleString()}</span>
            </div>

            <div className="border border-[#E5DFD4] p-3.5">
              <span className="text-[11px] text-[#8A8278] block mb-0.5">+10% savings rate</span>
              <span className="text-sm font-semibold text-[#1A1714] font-heading">€{Math.round(sc10pctReal).toLocaleString()}</span>
              <span className="text-[10px] text-[#3D6B54] block mt-0.5">+€{Math.round(sc10pctReal - baselineReal).toLocaleString()}</span>
            </div>

            <div className="border border-[#E5DFD4] p-3.5">
              <span className="text-[11px] text-[#8A8278] block mb-0.5">Double contributions</span>
              <span className="text-sm font-semibold text-[#1A1714] font-heading">€{Math.round(scDoubleReal).toLocaleString()}</span>
              <span className="text-[10px] text-[#3D6B54] block mt-0.5">+€{Math.round(scDoubleReal - baselineReal).toLocaleString()}</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
