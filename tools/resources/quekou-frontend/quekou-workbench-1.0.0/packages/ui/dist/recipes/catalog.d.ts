export declare const recipeCatalog: readonly [{
    readonly id: "overview";
    readonly name: "Overview";
    readonly label: "经营总览";
    readonly sequence: readonly ["PageHeader", "KpiRow", "TrendPanel + BreakdownPanel", "ActivityFeed"];
}, {
    readonly id: "list";
    readonly name: "List";
    readonly label: "项目列表";
    readonly sequence: readonly ["PageHeader", "QueryBar", "RecordTable", "PaginationBar"];
}, {
    readonly id: "detail";
    readonly name: "Detail";
    readonly label: "项目详情";
    readonly sequence: readonly ["PageHeader", "EntitySummary", "Tabs", "ActivityFeed / RelatedRecords"];
}, {
    readonly id: "settings";
    readonly name: "Settings";
    readonly label: "工作区设置";
    readonly sequence: readonly ["PageHeader", "SettingsNav + SettingsSection", "DangerZone"];
}];
export type RecipeId = typeof recipeCatalog[number]['id'];
export declare const blockCatalog: readonly ["KpiRow", "TrendPanel", "BreakdownPanel", "ActivityFeed", "QueryBar", "RecordTable", "PaginationBar", "EntitySummary", "RelatedRecords", "SettingsNav", "SettingsSection", "DangerZone"];
