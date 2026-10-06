import {forwardRef,useRef,useState} from 'react';
import {TriangleAlert} from 'lucide-react';
import {Button} from '../components/Button';import {Dialog} from '../components/Dialog';import {Input} from '../components/Input';
import {useThemeAttributes,type ThemeOverrides} from '../internal/foundation';
export interface DangerZoneProps extends ThemeOverrides {title:string;description:string;actionLabel:string;confirmText:string;confirmDescription:string;onConfirm:()=>void|Promise<void>;disabled?:boolean}
export const DangerZone=forwardRef<HTMLElement,DangerZoneProps>(function DangerZone({title,description,actionLabel,confirmText,confirmDescription,onConfirm,disabled=false,density,surfaceMode},ref){
 const attrs=useThemeAttributes({density,surfaceMode}),[open,setOpen]=useState(false),[value,setValue]=useState(''),[pending,setPending]=useState(false),[error,setError]=useState('');
 const running=useRef(false);
 const confirm=async()=>{if(running.current||disabled||value!==confirmText||!confirmText.trim())return;running.current=true;setPending(true);setError('');
  try{await onConfirm();setOpen(false);}catch{setError('操作未完成，请核对结果后重试。');}finally{running.current=false;setPending(false);}
 };
 return <section {...attrs} ref={ref} data-block="DangerZone" className="qk-danger-zone"><div><h2><TriangleAlert className="qk-icon" aria-hidden="true"/>{title}</h2><p>{description}</p></div>
 <Button className="qk-danger-button" disabled={disabled||!confirmText.trim()} onClick={()=>{setValue('');setError('');setOpen(true);}}>{actionLabel}</Button>
 <Dialog title={actionLabel} description={confirmDescription} open={open} onOpenChange={next=>{if(!running.current)setOpen(next);}} footer={<><Button disabled={pending} onClick={()=>setOpen(false)}>取消</Button><Button className="qk-danger-button" loading={pending} disabled={value!==confirmText||disabled||!confirmText.trim()} onClick={confirm}>确认{actionLabel}</Button></>}>
 <Input label={`请输入“${confirmText}”以确认`} disabled={pending} value={value} onChange={e=>setValue(e.target.value)} autoComplete="off"/>
 {error&&<p className="qk-error qk-description" role="alert">{error}</p>}
 </Dialog></section>;
});
