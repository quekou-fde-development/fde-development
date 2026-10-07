import { type ThemeOverrides } from '../internal/foundation';
export interface PaginationBarProps extends ThemeOverrides {
    page: number;
    pageSize: number;
    total: number;
    selectedCount?: number;
    onPageChange: (page: number) => void;
    onPageSizeChange: (size: number) => void;
}
export declare const PaginationBar: import("react").ForwardRefExoticComponent<PaginationBarProps & import("react").RefAttributes<HTMLDivElement>>;
