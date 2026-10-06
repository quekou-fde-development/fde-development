import { type ThemeOverrides } from '../internal/foundation';
export interface CommandItem {
    id: string;
    label: string;
    keywords?: string;
    onSelect: () => void;
}
export interface CommandPaletteProps extends ThemeOverrides {
    items: readonly CommandItem[];
    open?: boolean;
    defaultOpen?: boolean;
    onOpenChange?: (open: boolean) => void;
    shortcut?: boolean;
    title?: string;
    className?: string;
}
export declare const CommandPalette: import("react").ForwardRefExoticComponent<CommandPaletteProps & import("react").RefAttributes<HTMLDialogElement>>;
