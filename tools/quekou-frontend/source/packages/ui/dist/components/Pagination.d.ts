import { type HTMLAttributes } from 'react';
import { type ThemeOverrides } from '../internal/foundation';
export interface PaginationProps extends HTMLAttributes<HTMLElement>, ThemeOverrides {
    page: number;
    pageCount: number;
    onPageChange: (page: number) => void;
}
export declare const Pagination: import("react").ForwardRefExoticComponent<PaginationProps & import("react").RefAttributes<HTMLElement>>;
