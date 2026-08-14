import React from 'react';
import type { LucideIcon } from 'lucide-react';
import {
  ArrowLeftRight,
  Banknote,
  Briefcase,
  Car,
  CircleDot,
  Clapperboard,
  Coins,
  Dumbbell,
  Gift,
  GraduationCap,
  HeartPulse,
  Home,
  Landmark,
  Plane,
  Receipt,
  Shield,
  ShoppingBag,
  ShoppingBasket,
  Smartphone,
  Tag,
  TrendingUp,
  Utensils,
  Wallet,
  Zap,
} from 'lucide-react';

const ICONS: Record<string, LucideIcon> = {
  Salary: Banknote,
  Freelance: Briefcase,
  'Other Income': Wallet,
  'Rent & Housing': Home,
  Groceries: ShoppingBasket,
  Transport: Car,
  'Dining Out': Utensils,
  'Travel & Vacation': Plane,
  Entertainment: Clapperboard,
  Subscriptions: Smartphone,
  'Sports & Fitness': Dumbbell,
  Healthcare: HeartPulse,
  Insurance: Shield,
  Utilities: Zap,
  Shopping: ShoppingBag,
  Education: GraduationCap,
  'Gifts & Donations': Gift,
  'Taxes & Fees': Receipt,
  Cash: Coins,
  'Other Expense': CircleDot,
  'Depot Transfer': Landmark,
  'Savings & Investments': TrendingUp,
  'Internal Transfer': ArrowLeftRight,
  'From personal accounts': ArrowLeftRight,
};

interface CategoryIconProps {
  name?: string;
  className?: string;
}

export const CategoryIcon: React.FC<CategoryIconProps> = ({
  name,
  className = 'w-3.5 h-3.5',
}) => {
  const Icon = (name && ICONS[name]) || Tag;
  return <Icon className={className} strokeWidth={1.6} />;
};
