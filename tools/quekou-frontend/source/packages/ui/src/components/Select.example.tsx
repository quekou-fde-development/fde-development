import {useState} from 'react';import {Select} from '@quekou/ui';
export function SelectExample(){const [value,setValue]=useState('delivery');return <Select label="项目阶段" value={value} onChange={e=>setValue(e.target.value)} options={[{value:'discovery',label:'需求调研'},{value:'delivery',label:'交付实施'},{value:'accepted',label:'完成验收'}]} hint="支持方向键选择"/>}
