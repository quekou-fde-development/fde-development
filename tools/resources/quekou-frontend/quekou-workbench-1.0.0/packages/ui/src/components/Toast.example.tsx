import {useState} from 'react';import {Toast} from '@quekou/ui';import {Button} from '@quekou/ui';
export function ToastExample(){const [open,setOpen]=useState(false);return <><Button onClick={()=>setOpen(true)}>显示操作反馈</Button><Toast open={open} onDismiss={()=>setOpen(false)} status="success" title="演示设置已保存">停留或聚焦通知时暂停自动关闭。</Toast></>}
