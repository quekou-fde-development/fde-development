export const recipeCatalog=[
 {id:'overview',name:'Overview',label:'经营总览',sequence:['PageHeader','KpiRow','TrendPanel + BreakdownPanel','ActivityFeed']},
 {id:'list',name:'List',label:'项目列表',sequence:['PageHeader','QueryBar','RecordTable','PaginationBar']},
 {id:'detail',name:'Detail',label:'项目详情',sequence:['PageHeader','EntitySummary','Tabs','ActivityFeed / RelatedRecords']},
 {id:'settings',name:'Settings',label:'工作区设置',sequence:['PageHeader','SettingsNav + SettingsSection','DangerZone']},
] as const;
export type RecipeId=typeof recipeCatalog[number]['id'];
export const blockCatalog=['KpiRow','TrendPanel','BreakdownPanel','ActivityFeed','QueryBar','RecordTable','PaginationBar','EntitySummary','RelatedRecords','SettingsNav','SettingsSection','DangerZone'] as const;
