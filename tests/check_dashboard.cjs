/* Smoke-test the actual page scripts against their published data. */
const fs = require("node:fs");
const vm = require("node:vm");
const assert = require("node:assert/strict");

async function check(page, entry, required) {
  const nodes = new Map();
  const node = () => ({innerHTML:"", textContent:"", append(){}, prepend(){}});
  const context = vm.createContext({
    console,
    document: {querySelector(s) {if(!nodes.has(s))nodes.set(s,node());return nodes.get(s);},
      querySelectorAll(){return [];}, createElement:node},
    Chart: class {destroy(){}},
    fetch: async path => ({ok:true, json:async()=>JSON.parse(fs.readFileSync("docs/"+path,"utf8"))}),
  });
  const html = fs.readFileSync("docs/"+page,"utf8");
  for (const match of html.matchAll(/<script([^>]*)>([\s\S]*?)<\/script>/g)) {
    const src = match[1].match(/src="([^"]+)"/)?.[1];
    if (src?.startsWith("https:"))continue;
    const code = src ? fs.readFileSync("docs/"+src.split("?")[0],"utf8") : match[2];
    if (!src && code.trim().startsWith("init"))continue;
    vm.runInContext(code,context);
  }
  await vm.runInContext(entry,context);
  for (const selector of required) {
    const value=nodes.get(selector);
    assert(value && (value.innerHTML || value.textContent),page+": empty "+selector);
    assert(!value.innerHTML.includes("NaN"),page+": NaN "+selector);
  }
  console.log("PASS",page);
}
(async()=>{
  await check("chatgpt.html",'initDashboard("data/chatgpt.json")',
    ["#summary","#strategy-details","#history-body","#status"]);
  await check("academic.html",'initDashboard("data/academic.json")',
    ["#summary","#strategy-details","#history-body","#status"]);
  await check("index.html",'initOverview(["data/academic.json","data/chatgpt.json","data/claude.json"])',
    ["#summary","#metrics-body","#group-breakdown","#status"]);
})().catch(error=>{console.error(error);process.exitCode=1;});
