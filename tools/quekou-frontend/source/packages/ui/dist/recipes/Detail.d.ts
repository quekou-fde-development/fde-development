import { type RefAttributes, type ReactElement } from 'react';
import { type PageHeaderProps } from '../components/PageHeader';
import { type EntitySummaryProps } from '../blocks/EntitySummary';
import { type ActivityFeedProps } from '../blocks/ActivityFeed';
import { type RelatedRecordsProps } from '../blocks/RelatedRecords';
import { type ThemeOverrides } from '../internal/foundation';
export type DetailTab = 'timeline' | 'related';
export interface DetailProps<T> extends ThemeOverrides {
    header: PageHeaderProps;
    summary: EntitySummaryProps;
    activity: ActivityFeedProps;
    related: RelatedRecordsProps<T>;
    activeTab: DetailTab;
    onTabChange: (tab: DetailTab) => void;
}
export declare const Detail: <T>(props: DetailProps<T> & RefAttributes<HTMLDivElement>) => ReactElement;
