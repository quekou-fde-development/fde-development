import {useState} from 'react';import {Checkbox} from '@quekou/ui';
export function CheckboxExample(){const [checked,setChecked]=useState(false);return <div className="qk-example-stack"><Checkbox label="我已核对交付清单" checked={checked} onChange={e=>setChecked(e.target.checked)}/><Checkbox label="部分任务已选择" indeterminate readOnly/><Checkbox label="此项暂不可选" disabled/></div>}
