import {Popover} from '@quekou/ui';import {Checkbox} from '@quekou/ui';
export function PopoverExample(){return <Popover label="显示选项" trigger="打开显示选项"><div className="qk-example-stack"><strong>显示内容</strong><Checkbox label="显示项目负责人" defaultChecked/><Checkbox label="显示交付进度" defaultChecked/><p className="qk-muted">按 Esc 关闭，或点击面板外。</p></div></Popover>}
