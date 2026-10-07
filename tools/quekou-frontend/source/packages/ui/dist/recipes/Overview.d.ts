import { type PageHeaderProps } from '../components/PageHeader';
import { type KpiRowProps } from '../blocks/KpiRow';
import { type TrendPanelProps } from '../blocks/TrendPanel';
import { type BreakdownPanelProps } from '../blocks/BreakdownPanel';
import { type ActivityFeedProps } from '../blocks/ActivityFeed';
import { type ThemeOverrides } from '../internal/foundation';
export interface OverviewProps extends ThemeOverrides {
    header: PageHeaderProps;
    kpis: KpiRowProps;
    trend: TrendPanelProps;
    breakdown: BreakdownPanelProps;
    activity: ActivityFeedProps;
}
export declare const Overview: import("react").ForwardRefExoticComponent<OverviewProps & import("react").RefAttributes<HTMLDivElement>>;
