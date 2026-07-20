// Display labels, kept separate from the data export so wording changes
// don't require re-running the pipeline. zh-Hans only for now -- six-language
// support is architected for (PRD v1.2 C10, template-based localization) but
// gated on HRL-010 (native-speaker review of the term glossary), not yet done.

export const STATUS_LABEL = {
  A1: '自动收集',
  A2: '机器关联',
  A3: '多方印证',
  A4: '权威记录',
  AX: '存在争议',
  AF: '错误归属/谣言',
};

export const STATUS_BLURB = {
  A1: '系统已保存公开来源，但核心信息尚不足以形成多方印证的事件档案。',
  A2: '多个来源或媒体被系统归并为同一候选事件，但部分时间、地点或背景仍未确认。',
  A3: '多个相互独立的公开来源支持该事件的核心事实，未发现重大反证。',
  A4: '一个或多个权威公开来源（政府、警方、法院或正式机构）记录了以下核心事实。',
  AX: '不同公开来源对该事件的核心事实存在重大冲突，页面分别列出支持信息与反证，不作单一结论。',
  AF: '经核实，相关指控被证实为虚假或错误归属，本页面为纠错记录，防止同一错误再次传播。',
};

export const HARM_LABEL = {
  beating: '殴打', burning: '纵火/烧伤', scalding: '烫伤', stabbing: '刺伤',
  poisoning: '投毒', suffocation: '窒息/勒颈', throwing_or_falling: '抛掷/坠落',
  dismemberment: '肢解/致残', starvation: '饥饿', abandonment: '遗弃',
  forced_fighting: '强迫争斗', content_motivated_abuse: '内容牟利式虐待',
  inhumane_capture: '非人道捕捉', inhumane_transport: '非人道运输',
  inhumane_killing: '非人道扑杀', medical_neglect: '医疗忽视', other_harm: '其他伤害',
};

export const CLAIM_TYPE_LABEL = {
  event_occurred: '事件是否发生', event_date: '事件日期', event_location: '事件地点',
  animal_species: '动物种类', animal_count: '动物数量', harm_method: '伤害方式',
  animal_death: '动物死亡情况', minor_involvement: '未成年人涉入',
  institutional_involvement: '机构涉入', official_response: '官方回应',
  rescue_outcome: '救助结果', legal_outcome: '法律处理结果', policy_response: '政策/机构回应',
};

export const SUPPORT_STATUS_LABEL = {
  supported: '获得支持', partially_supported: '部分支持',
  claimed_only: '仅为陈述（未验证）', contradicted: '存在矛盾', unknown: '未知',
};

export const SOURCE_TIER_LABEL = {
  '1': 'Tier 1 · 官方/权威', '2': 'Tier 2 · 专业媒体', '3': 'Tier 3 · 第一手/社交',
  '4': 'Tier 4 · 二次传播',
};

export const PUBLICATION_THRESHOLD = { A1: 40, A2: 55, A3: 70, A4: 85 };

export function isPublishable(incident) {
  if (incident.automation_status === 'AX' || incident.automation_status === 'AF') return false;
  const threshold = PUBLICATION_THRESHOLD[incident.automation_status];
  return threshold != null && incident.evidence_sufficiency_score >= threshold;
}

export function locationLabel(incident) {
  return [incident.province, incident.city].filter(Boolean).join(' · ') || '地点跨区域/未确定';
}
