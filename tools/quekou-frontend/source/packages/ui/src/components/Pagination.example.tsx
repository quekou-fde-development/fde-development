import {useState} from 'react';import {Pagination} from '@quekou/ui';
export function PaginationExample(){const [page,setPage]=useState(1);return <Pagination page={page} pageCount={12} onPageChange={setPage}/>} 
