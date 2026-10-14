const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
const src=fs.readFileSync('campsite_journal/static/app.js','utf8');const nodes={'#search':{value:''},'#head':{},'#rows':{},'#zoomImage':{},'#zoom':{showModal(){this.open=true}}};
const records=[{id:'b',name:'나 캠핑장',platform:'캠핏',price:9000,photos:[]},{id:'a',name:'가 캠핑장',platform:'네이버 예약',price:1000,photos:[]},{id:'c',name:'다 캠핑장',platform:'캠핏',price:9000,photos:[]}];const c={state:{records},sortBy:null,sortCollator:new Intl.Collator('ko-KR',{numeric:true,sensitivity:'base'}),$:s=>nodes[s],showDetail(){throw Error('A photo click must not open details')},render(){}};vm.createContext(c);
vm.runInContext(src.slice(src.indexOf('function filtered()'),src.indexOf('\nfunction link')),c);
vm.runInContext(src.slice(src.indexOf("$('#head').onclick="),src.indexOf(";$('#rows').onkeydown")),c);
const clickHeader=k=>nodes['#head'].onclick({target:{closest:()=>({dataset:{sort:k}})}});
clickHeader('price');assert.deepEqual(Array.from(c.filtered(),r=>r.id),['a','b','c']);clickHeader('price');assert.deepEqual(Array.from(c.filtered(),r=>r.id),['b','c','a']);clickHeader('price');assert.deepEqual(Array.from(c.filtered(),r=>r.id),['b','a','c']);nodes['#search'].value='캠핏';assert.deepEqual(Array.from(c.filtered(),r=>r.id),['b','c']);nodes['#search'].value='네이버';assert.deepEqual(Array.from(c.filtered(),r=>r.id),['a']);
nodes['#rows'].onclick({target:{closest:s=>s==='a'?null:s==='[data-mini-zoom]'?{dataset:{miniZoom:'photo-id'},alt:'사진'}:null}});assert.equal(nodes['#zoom'].open,true);assert.equal(nodes['#zoomImage'].src,'photos/photo-id');
console.log('List: three-step sorting, stable default order, platform search and direct photo enlargement passed.');
