import {useState} from 'react';import {ProgressBar} from '@quekou/ui';import {Button} from '@quekou/ui';
export function ProgressBarExample(){const [value,setValue]=useState(72);return <div className="qk-example-stack"><ProgressBar label="验收材料准备进度" value={value}/><Button size="sm" onClick={()=>setValue(v=>v>=100?0:Math.min(v+10,100))}>增加进度</Button></div>}
