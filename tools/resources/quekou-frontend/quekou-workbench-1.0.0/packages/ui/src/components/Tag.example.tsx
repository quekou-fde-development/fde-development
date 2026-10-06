import {useState} from 'react';import {Tag} from '@quekou/ui';import {Button} from '@quekou/ui';
export function TagExample(){const [shown,setShown]=useState(true);return <div className="qk-example-row"><Tag label="重点客户"/>{shown?<Tag label="本周交付" onRemove={()=>setShown(false)}/>:<Button size="sm" onClick={()=>setShown(true)}>恢复标签</Button>}</div>}
