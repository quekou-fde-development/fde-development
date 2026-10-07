export type ProjectStatus = '正常推进' | '存在风险' | '待验收' | '已完成';
export interface Project { id: string; name: string; client: string; category: string; owner: string; amount: number; progress: number; status: ProjectStatus; due: string }
export const projects: Project[] = [
  { id:'QK-1024',name:'生产数据驾驶舱',client:'远川制造',category:'制造',owner:'林悦',amount:186000,progress:72,status:'正常推进',due:'2026-09-30' },
  { id:'QK-1025',name:'智能客服工作台',client:'星野零售',category:'零售',owner:'周明',amount:148000,progress:45,status:'存在风险',due:'2026-09-29' },
  { id:'QK-1026',name:'供应链协同平台',client:'知行科技',category:'科技',owner:'陈曦',amount:210000,progress:90,status:'待验收',due:'2026-09-30' },
  { id:'QK-1027',name:'人效分析系统',client:'清禾集团',category:'服务',owner:'林悦',amount:96000,progress:64,status:'正常推进',due:'2026-10-08' },
  { id:'QK-1028',name:'设备巡检助手',client:'远川制造',category:'制造',owner:'许诺',amount:128000,progress:100,status:'已完成',due:'2026-09-25' },
  { id:'QK-1029',name:'销售线索中台',client:'云序科技',category:'科技',owner:'周明',amount:112000,progress:38,status:'正常推进',due:'2026-10-12' },
  { id:'QK-1030',name:'仓储追溯系统',client:'禾木物流',category:'物流',owner:'陈曦',amount:168000,progress:56,status:'存在风险',due:'2026-10-06' },
  { id:'QK-1031',name:'财务对账自动化',client:'星野零售',category:'零售',owner:'许诺',amount:78000,progress:100,status:'已完成',due:'2026-09-24' },
  { id:'QK-1032',name:'客户成功看板',client:'知行科技',category:'科技',owner:'林悦',amount:88000,progress:82,status:'待验收',due:'2026-10-09' },
  { id:'QK-1033',name:'知识运营平台',client:'清禾集团',category:'服务',owner:'周明',amount:72000,progress:24,status:'正常推进',due:'2026-10-15' },
];
export const kpis = [
  {label:'项目总额',value:'128.6',unit:'万元',change:'+12.8%',note:'较去年同期',trend:[15,12,19,17,26,23,31,36,32,45,42,51]},
  {label:'交付项目',value:'10',unit:'个',change:'+2 个',note:'较去年同期',trend:[12,12,18,18,18,28,28,34,34,42,42,48]},
  {label:'平均完成度',value:'67.1',unit:'%',change:'+8.4pp',note:'较去年同期',trend:[18,16,20,26,23,29,34,32,38,43,41,48]},
  {label:'风险项目',value:'2',unit:'个',change:'−1 个',note:'较去年同期',trend:[48,43,46,36,32,35,26,25,20,23,17,17]},
];
export const actual = [38,42,40,54,49,63,59,72,66,80,76,92];
export const target = [32,37,42,47,52,57,62,67,72,77,82,87];
export const statusKind: Record<ProjectStatus,string> = {'正常推进':'status-info','存在风险':'status-warning','待验收':'status-neutral','已完成':'status-success'};
export const number = new Intl.NumberFormat('zh-CN');
