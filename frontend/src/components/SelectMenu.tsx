import React, { useEffect, useId, useRef, useState } from 'react';
import { createPortal } from 'react-dom';
import { Check, ChevronDown } from 'lucide-react';

export interface SelectOption {
  value: string;
  label: string;
  icon?: React.ReactNode;
  hint?: string;
}

interface SelectMenuProps {
  value: string;
  options: SelectOption[];
  onChange: (value: string) => void;
  variant?: 'field' | 'inline';
  placeholder?: string;
  className?: string;
  'aria-label'?: string;
}

export const SelectMenu: React.FC<SelectMenuProps> = ({
  value,
  options,
  onChange,
  variant = 'field',
  placeholder = 'Select',
  className = '',
  'aria-label': ariaLabel,
}) => {
  const [open, setOpen] = useState(false);
  const buttonRef = useRef<HTMLButtonElement>(null);
  const menuRef = useRef<HTMLDivElement>(null);
  const menuId = useId();
  const [pos, setPos] = useState({ top: 0, left: 0, width: 200, maxHeight: 280 });

  const selected = options.find((opt) => opt.value === value);

  const placeMenu = () => {
    const button = buttonRef.current;
    if (!button) return;
    const rect = button.getBoundingClientRect();
    const width = Math.max(rect.width, variant === 'inline' ? 220 : 160);
    const spaceBelow = window.innerHeight - rect.bottom - 12;
    const spaceAbove = rect.top - 12;
    const maxHeight = Math.min(280, Math.max(spaceBelow, spaceAbove, 120));
    const openUp = spaceBelow < 160 && spaceAbove > spaceBelow;
    const top = openUp ? rect.top - 4 - maxHeight : rect.bottom + 4;
    let left = rect.left;
    if (left + width > window.innerWidth - 8) {
      left = Math.max(8, window.innerWidth - width - 8);
    }
    setPos({ top, left, width, maxHeight });
  };

  useEffect(() => {
    if (!open) return;
    placeMenu();

    const onPointer = (event: MouseEvent) => {
      const target = event.target as Node;
      if (buttonRef.current?.contains(target) || menuRef.current?.contains(target)) return;
      setOpen(false);
    };
    const onKey = (event: KeyboardEvent) => {
      if (event.key === 'Escape') setOpen(false);
    };
    const onReposition = () => placeMenu();

    document.addEventListener('mousedown', onPointer);
    document.addEventListener('keydown', onKey);
    window.addEventListener('resize', onReposition);
    window.addEventListener('scroll', onReposition, true);
    return () => {
      document.removeEventListener('mousedown', onPointer);
      document.removeEventListener('keydown', onKey);
      window.removeEventListener('resize', onReposition);
      window.removeEventListener('scroll', onReposition, true);
    };
  }, [open]);

  const triggerClass =
    variant === 'field'
      ? `cream-input inline-flex items-center gap-2 px-3 text-xs font-medium cursor-pointer ${
          selected ? 'text-[#1A1714]' : 'text-[#8A8278]'
        } ${className}`
      : `inline-flex items-center gap-1.5 text-[11px] font-medium rounded-sm px-1.5 py-1 -mx-1.5 cursor-pointer hover:bg-[#F3F0EA] ${
          selected ? 'text-[#1A1714]' : 'text-[#8C4A3A]'
        } ${className}`;

  return (
    <>
      <button
        ref={buttonRef}
        type="button"
        aria-haspopup="listbox"
        aria-expanded={open}
        aria-controls={menuId}
        aria-label={ariaLabel}
        onClick={() => setOpen((prev) => !prev)}
        className={triggerClass}
      >
        {selected?.icon}
        <span className="truncate">{selected?.label || placeholder}</span>
        <ChevronDown
          className={`w-3 h-3 ml-auto shrink-0 ${open ? 'text-[#1A1714]' : 'text-[#8A8278]'}`}
          strokeWidth={1.7}
        />
      </button>

      {open &&
        createPortal(
          <div
            ref={menuRef}
            id={menuId}
            role="listbox"
            aria-label={ariaLabel}
            className="fixed z-[80] bg-white border border-[#E5DFD4] py-1 overflow-y-auto"
            style={{
              top: pos.top,
              left: pos.left,
              width: pos.width,
              maxHeight: pos.maxHeight,
              boxShadow: '0 10px 28px -12px rgba(26, 23, 20, 0.22)',
            }}
          >
            {options.map((opt) => {
              const isSelected = opt.value === value;
              return (
                <button
                  key={opt.value}
                  type="button"
                  role="option"
                  aria-selected={isSelected}
                  onClick={() => {
                    onChange(opt.value);
                    setOpen(false);
                  }}
                  className={`w-full flex items-center gap-2 px-2.5 py-2 text-xs text-left ${
                    isSelected ? 'bg-[#F3F0EA] text-[#1A1714]' : 'text-[#1A1714] hover:bg-[#F6F4EF]'
                  }`}
                >
                  {opt.icon}
                  <span className="truncate flex-1">{opt.label}</span>
                  {opt.hint && (
                    <span className="text-[10px] text-[#8A8278] shrink-0">{opt.hint}</span>
                  )}
                  {isSelected && (
                    <Check className="w-3 h-3 text-[#8F7848] shrink-0" strokeWidth={1.8} />
                  )}
                </button>
              );
            })}
          </div>,
          document.body
        )}
    </>
  );
};
