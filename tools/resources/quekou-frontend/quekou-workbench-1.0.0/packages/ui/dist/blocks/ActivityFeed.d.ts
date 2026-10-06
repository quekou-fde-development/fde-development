import { type StatusKind } from '../components/Badge';
import { type ThemeOverrides } from '../internal/foundation';
export interface ActivityItem {
    id: string;
    title: string;
    detail: string;
    actor: string;
    time: string;
    status: StatusKind;
    statusLabel: string;
    onOpen?: () => void;
}
export interface ActivityFeedProps extends ThemeOverrides {
    title: string;
    description?: string;
    items: readonly ActivityItem[];
    variant?: 'feed' | 'timeline';
    loading?: boolean;
}
export declare const ActivityFeed: import("react").ForwardRefExoticComponent<ActivityFeedProps & import("react").RefAttributes<HTMLElement>>;
