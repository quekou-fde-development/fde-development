import { type PageHeaderProps } from '../components/PageHeader';
import { type SettingsNavProps } from '../blocks/SettingsNav';
import { type SettingsSectionProps } from '../blocks/SettingsSection';
import { type DangerZoneProps } from '../blocks/DangerZone';
import { type ThemeOverrides } from '../internal/foundation';
export interface SettingsProps extends ThemeOverrides {
    header: PageHeaderProps;
    navigation: SettingsNavProps;
    sections: readonly SettingsSectionProps[];
    danger: DangerZoneProps;
    dirty: boolean;
    savedMessage?: string;
    onSave: () => void;
    onCancel: () => void;
}
export declare const Settings: import("react").ForwardRefExoticComponent<SettingsProps & import("react").RefAttributes<HTMLDivElement>>;
