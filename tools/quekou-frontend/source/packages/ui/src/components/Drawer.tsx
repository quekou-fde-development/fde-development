import {forwardRef} from 'react';
import {Dialog,type DialogProps} from './Dialog';
import {cx} from '../internal/foundation';
export interface DrawerProps extends DialogProps {}
export const Drawer=forwardRef<HTMLDialogElement,DrawerProps>(function Drawer({className,...props},ref){return <Dialog {...props} ref={ref} className={cx('qk-drawer',className)}/>;});
