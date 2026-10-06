import { type SelectOption } from '../components/Select';
import { type ThemeOverrides } from '../internal/foundation';
interface FieldBase {
    id: string;
    label: string;
    hint?: string;
    error?: string;
    disabled?: boolean;
}
export type SettingsField = (FieldBase & {
    kind: 'text';
    value: string;
    onChange: (value: string) => void;
    type?: 'text' | 'email' | 'url';
    required?: boolean;
    maxLength?: number;
}) | (FieldBase & {
    kind: 'select';
    value: string;
    onChange: (value: string) => void;
    options: readonly SelectOption[];
}) | (FieldBase & {
    kind: 'checkbox';
    value: boolean;
    onChange: (value: boolean) => void;
});
export interface SettingsSectionProps extends ThemeOverrides {
    id: string;
    title: string;
    description: string;
    fields: readonly SettingsField[];
}
export declare const SettingsSection: import("react").ForwardRefExoticComponent<SettingsSectionProps & import("react").RefAttributes<HTMLElement>>;
export {};
