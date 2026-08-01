// Bilingual UI strings, hand-translated (not machine-translated) because this
// is the highest-visibility text on the site -- every visitor sees the nav
// and homepage before anything else. Machine translation is reserved for
// bulk content fields (incident claims, judgment summaries) where volume
// makes hand-translation impractical; see pipeline/translate_content.py.
//
// Both languages are hand-authored pairs in this one table (not "English
// dictionary + read Chinese from the DOM") so the toggle script never has to
// guess -- it just swaps text between two known strings for a key. Default
// locale is English: t(key) is what .astro files render into the static
// HTML, and data-en/data-zh attributes carry both so the client-side toggle
// (Layout.astro) can swap without a page reload.

export const STRINGS = {
  'nav.incidents': { en: 'Incidents', zh: '事件' },
  'nav.census': { en: 'Judgments', zh: '判决书' },
  'nav.methodology': { en: 'Methodology', zh: '方法与数据' },
  'nav.appeals': { en: 'Appeals', zh: '申诉与更正' },
  'nav.submit': { en: 'Submit a Tip', zh: '提交线索' },

  'site.title_small': { en: 'Animal Harm Incident Database', zh: '动物伤害事件数据库' },

  'footer.disclaimer': {
    en: 'This website uses automated tools to collect, archive, merge, and analyze publicly available internet information. Incident pages reflect the public sources the system found and their relationships to each other at a given time -- they do not constitute a judicial finding, an independent investigative conclusion, or a conviction of any individual. The system may miss incidents, merge them incorrectly, or reflect source bias.',
    zh: '本网站使用自动化工具收集、保存、归并和分析公开互联网信息。事件页面反映系统在指定时间找到的公开来源及其相互关系，不构成司法认定、独立调查结论或对任何个人的定罪。系统可能出现遗漏、误归并或来源偏差。',
  },
  'footer.reachability': {
    en: 'This site may be unreliably reachable from some mainland China networks. If you have trouble, the underlying dataset is available directly via ',
    zh: '本站在部分中国大陆网络环境下可能访问不稳定；如遇到问题，可通过 ',
  },
  'footer.reachability_end': { en: '.', zh: ' 直接获取研究数据。' },
  'footer.zenodo_link_text': { en: 'the Zenodo dataset', zh: 'Zenodo 数据集' },
  'footer.preview': { en: 'Preview build', zh: '预览构建' },
  'footer.not_public': { en: 'not publicly deployed', zh: '未公开部署' },

  'home.h1': { en: 'Animal Harm Incident Database', zh: '动物伤害事件数据库' },
  'home.intro_1': {
    en: 'AHID continuously discovers, archives, deduplicates, merges, and cross-verifies publicly available internet information about animal harm in mainland China, showing sources, evidence sufficiency, conflicts, and institutional responses transparently. The first-release corpus, AHID-CN, is made of two complementary sub-corpora: an ',
    zh: 'AHID 持续发现、保存、去重、归并并交叉核验中国大陆动物伤害相关的公开互联网信息，透明展示来源、证据充分度、冲突与机构回应。首期语料 AHID-CN，由两个互补的子语料构成：依赖公开报道的',
  },
  'home.intro_incidents_link': { en: 'incident database', zh: '事件库' },
  'home.intro_2': {
    en: ' (broad coverage, but not a reproducible sample), and a ',
    zh: '（覆盖面广，但无法复现的样本框），与有明确抽样框的',
  },
  'home.intro_census_link': { en: 'judgment census', zh: '判决书 census' },
  'home.intro_3': {
    en: ' with an explicit sampling frame (reproducible, but limited to cases that reached criminal prosecution).',
    zh: '（可复现，但只覆盖进入司法程序的案件）。',
  },

  'home.disclaimer_title': { en: 'About this site', zh: '关于本站' },
  'home.disclaimer_body': {
    en: 'This website uses automated tools to collect, archive, merge, and analyze publicly available internet information. Incident pages reflect the public sources the system found and their relationships to each other at a given time -- they do not constitute a judicial finding, an independent investigative conclusion, or a conviction of any individual. The system may miss incidents, merge them incorrectly, mistranslate, or reflect source bias. Identifying information about minors and ordinary individuals is not published as a rule. The database records publicly observable information -- it does not represent the true incidence rate, and should not be used to rank regions or groups.',
    zh: '本网站使用自动化工具收集、保存、归并和分析公开互联网信息。事件页面反映系统在指定时间找到的公开来源及其相互关系，不构成司法认定、独立调查结论或对任何个人的定罪。系统可能出现遗漏、误归并、翻译错误或来源偏差。涉及未成年人和普通个人的身份信息原则上不会公开。数据库记录公开可观察信息，不代表真实发生率，也不应直接用于地区或群体排名。',
  },

  'home.stat.incidents': { en: 'merged incidents (including below publication threshold)', zh: '已归并事件（含未达发布门槛）' },
  'home.stat.publishable': { en: 'meet publication threshold', zh: '达到发布门槛' },
  'home.stat.provinces': { en: 'provinces involved', zh: '涉及省级行政区' },
  'home.stat.official_response': { en: 'have an official/institutional response on record', zh: '有官方/机构回应记录' },

  'home.section.latest': { en: 'Latest incidents meeting publication threshold', zh: '最新达到发布门槛的事件' },
  'home.date_unknown': { en: 'date undetermined', zh: '日期未确定' },
  'home.link.view_all_incidents': { en: 'View all {n} incidents →', zh: '查看全部 {n} 条事件 →' },

  'home.section.census': { en: 'Judgment census (the other sub-corpus)', zh: '判决书 census（另一个子语料）' },
  'home.census_body': {
    en: '{n} criminal judgments involving animal harm, from a full-corpus search of CAIL2018 (an explicit, reproducible sampling frame). Unlike the incident database above, which relies on public reporting, this covers only cases that reached criminal prosecution -- its single largest finding is that dog-theft-and-poisoning rings are prosecuted almost entirely as property crime, rarely as cruelty.',
    zh: '{n} 条涉动物伤害的刑事判决，全量检索自 CAIL2018（有明确抽样框、可复现）。与上方事件库依赖公开报道不同，这批数据只覆盖进入司法程序的案件——最大的单一发现：偷狗毒狗产业链几乎全部以盗窃、抢劫等财产罪起诉，极少以虐待罪论处。',
  },
  'home.link.view_all_census': { en: 'View all {n} judgments →', zh: '查看全部 {n} 条判决 →' },

  'home.section.bias': { en: 'Known biases', zh: '已知偏差' },
  'home.bias_body': {
    en: 'This round of data is a research-version pilot (Tier D, URL-driven backfill, not automated discovery) -- incident coverage depends on what the founder already knew about, systematically narrower than a future automated-discovery phase would achieve. More internet exposure does not mean more real occurrences; internet-active regions may be over-represented. {n} incidents are flagged as disputed or misattributed -- see individual incident pages and the ',
    zh: '本轮数据为研究版试点（Tier D，URL 驱动回填，非自动发现），事件覆盖面取决于创始人已知的线索，系统性小于未来自动发现阶段。互联网曝光多不等于真实发生多；网络活跃地区可能被过度收录；{n} 条事件被标记为存在争议或错误归属，详见各事件页面与',
  },
  'home.bias_methodology_link': { en: 'Methodology & Data', zh: '方法与数据' },
  'home.bias_end': { en: ' page.', zh: '页。' },

  'census.title': { en: 'Judgment Census', zh: '判决书 census' },
  'census.intro_1': { en: 'Full-corpus search results from ', zh: '来自 ' },
  'census.intro_cail_link': { en: 'CAIL2018', zh: 'CAIL2018' },
  'census.intro_2': {
    en: ' (2.68 million Chinese criminal judgments published before 2018, an official research corpus from the "Law Research Cup" challenge). Unlike the incident page above, which relies on public reporting, this sub-corpus has an explicit sampling frame -- anyone downloading the same dataset and running the same search reproduces the same candidate set. All {n} records were verified by hand before inclusion, see §13 of the ',
    zh: '（268 万份 2018 年前公布的单被告人刑事判决，"法研杯"官方研究语料）的全量检索结果。与上方"事件"页面依赖的公开报道不同，这批数据有明确的抽样框——任何人下载同一数据集、跑同一检索式，都能复现同一候选集。全部 {n} 条经人工核实后收录，详见',
  },
  'census.intro_methodology_link': { en: 'Methodology & Data', zh: '方法与数据' },
  'census.intro_3': { en: ' page.', zh: '页 §13。' },

  'census.about_title': { en: 'About this table', zh: '关于这批数据' },
  'census.about_body': {
    en: 'This is an independent flat table -- it does not use the multi-source cross-verification and evidence-sufficiency scoring the incident pages above use (a court judgment is a single authoritative source; that scoring model does not apply). Each record carries evidence-transparency flags distinguishing "harm the judgment directly establishes" from "included by presumed pattern" and "an unverified allegation" -- open a record and read the flag notes, not just the category label.',
    zh: '这是一张独立的扁平表，不套用上方"事件"页面的多来源交叉核验与证据充分度评分（判决书是单一权威信源，那套评分不适用）。每条记录附带证据类型透明标记，区分"判决直接认定的伤害"与"按作案模式推定纳入""未经判决认定的声称"——点开记录查看完整判决事实文本与标记说明，不要只看分类标签。',
  },

  'census.stat.total': { en: 'judgments included', zh: '收录判决' },
  'census.stat.categories': { en: 'category types', zh: '分类类型' },
  'census.stat.poaching': { en: 'dog-theft/poaching cases', zh: '偷狗/偷猎类' },
  'census.stat.presumed': { en: 'presumed/unverified evidence cases', zh: '证据推定/未证实类' },

  'census.filter.all_categories': { en: 'All categories', zh: '全部分类' },
  'census.filter.all_animals': { en: 'All animal types', zh: '全部动物类型' },
  'census.filter.search_placeholder': { en: 'Search charges/summary keywords…', zh: '搜索罪名/摘要关键词…' },
  'census.animal_unknown': { en: 'animal type undetermined', zh: '动物类型未确定' },
  'census.count_line': { en: 'Showing {shown} / {total}', zh: '显示 {shown} / {total} 条' },

  'census.flag_label': { en: 'Evidence-transparency flags: ', zh: '证据透明标记：' },
  'census.flag.outcome_undocumented': {
    en: "The judgment did not state the animal's final fate, included by presumed pattern based on method/motive matching confirmed cases.",
    zh: '判决未明写动物最终结局，按作案手段/动机与已确认案例一致推定纳入。',
  },
  'census.flag.claim_unverified': {
    en: 'The allegation (e.g. poisoning) was not established as fact by the court -- the claim itself is what was counted.',
    zh: '相关指控（如下毒）未经判决认定为事实，采信声称本身计入。',
  },
  'census.flag.animal_not_confirmed_harmed': {
    en: 'Whether the animal itself was harmed was not established.',
    zh: '动物本身是否受伤未被证实。',
  },
  'census.flag.perpetrator_unconfirmed': {
    en: "The harm is real, but the perpetrator's identity was not established.",
    zh: '伤害真实发生，但加害人身份未坐实。',
  },
  'census.flag.recovered': { en: 'The animal was recovered after a completed theft.', zh: '盗窃既遂后动物被追回。' },
  'census.note_label': { en: 'Human review note: ', zh: '人工审核说明：' },
  'census.meta_line': {
    en: 'ID {id} · charge {charges} · motive {motive} · count {count} · AI confidence {confidence} · review {review}',
    zh: '编号 {id} · 罪名 {charges} · 动机 {motive} · 数量 {count} · AI 分类置信度 {confidence} · 审核方式 {review}',
  },
  'census.motive_unextracted': { en: 'not extracted', zh: '未提取' },
  'census.count_unknown': { en: 'undetermined', zh: '未确定' },
  'census.review.human': { en: 'human-reviewed', zh: '人工审核' },
  'census.review.auto': { en: 'high-confidence auto-included', zh: '高置信自动纳入' },
  'census.fact_untranslated': {
    en: 'The full judgment text below is the original Chinese legal document. Machine translation is not provided for it -- translation accuracy for legal text at this volume is not reliable enough to present as authoritative, and the original wording is what actually establishes the facts of the case.',
    zh: '以下判决事实全文为原始中文法律文书，不提供机器翻译——该体量下法律文本的翻译准确性不足以作为权威依据呈现，且原文措辞才是真正认定案件事实的依据。',
  },

  'incidents.title': { en: 'Incident List', zh: '事件列表' },
  'incidents.intro': {
    en: '{n} merged incidents on record. Filtering and sorting run client-side and send no requests.',
    zh: '共 {n} 条已归并事件。筛选与排序为客户端脚本，不发送任何请求。',
  },
  'incidents.filter.all_provinces': { en: 'All provinces', zh: '全部省份' },
  'incidents.filter.all_categories': { en: 'All animal types', zh: '全部动物类型' },
  'incidents.filter.all_statuses': { en: 'All statuses', zh: '全部状态' },
  'incidents.filter.minor_unrestricted': { en: 'Minor involvement: any', zh: '未成年人涉入：不限' },
  'incidents.filter.minor_yes': { en: 'Minor involved', zh: '涉及未成年人' },
  'incidents.filter.minor_no': { en: 'No minor involved', zh: '不涉及未成年人' },
  'incidents.disputed_badge': { en: 'Disputed', zh: '存在争议' },
  'incidents.af_placeholder': { en: '(AF: no actual harm -- see page notes)', zh: '（AF：无真实伤害，见页面说明）' },
  'incidents.evidence_sufficiency_label': { en: 'evidence sufficiency', zh: '证据充分度' },
};

export function T(key) {
  return STRINGS[key] || { en: key, zh: key };
}

function interp(s, vars) {
  let out = s;
  for (const [k, v] of Object.entries(vars)) {
    out = out.replaceAll(`{${k}}`, v);
  }
  return out;
}

// Astro-template convenience: returns the English default string (with {var}
// interpolation applied) for the visible static text position.
export function t(key, vars = {}) {
  return interp(T(key).en, vars);
}

// Companion to t() -- returns the interpolated Chinese counterpart, for a
// data-zh attribute the client-side toggle script reads on click.
export function tZh(key, vars = {}) {
  return interp(T(key).zh, vars);
}
