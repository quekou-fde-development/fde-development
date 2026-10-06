import { type KpiCardProps } from '../components/KpiCard';
import { type ThemeName, type ThemeOverrides } from '../internal/foundation';
export interface Insight {
    text: string;
    source: string;
    actionLabel?: string;
    onReview?: () => void;
}
export interface KpiRowProps extends ThemeOverrides {
    items: readonly [KpiCardProps, KpiCardProps, KpiCardProps, KpiCardProps];
    theme: ThemeName;
    insight?: Insight;
    loading?: boolean;
}
export declare function InsightNote({ insight }: {
    insight: Insight;
}): import("react/jsx-runtime").JSX.Element;
export declare const KpiRow: import("react").ForwardRefExoticComponent<KpiRowProps & import("react").RefAttributes<HTMLElement>>;
