export type MetricTone = 'cyan' | 'amber' | 'violet' | 'emerald';

export interface MetricCard {
  id: string;
  title: string;
  unit: string;
  value: number;
  precision?: number;
  delta: number;
  tone: MetricTone;
}

export interface TrendPoint {
  label: string;
  values: Record<string, number>;
}

export interface TrendSeriesConfig {
  name: string;
  key: string;
  type: 'line' | 'bar';
  color: string;
  yAxisIndex?: number;
  areaColor?: string;
}

export interface EventRecord {
  id: string;
  level: 'critical' | 'warning' | 'info';
  title: string;
  description: string;
  timestamp: string;
}

interface FieldDef {
  nodeid: string;
  description: string;
  unit: string;
  value: number;
  precision: number;
  amplitude: number;
  tone: MetricTone;
}

const FIELD_DEFS: Record<string, FieldDef> = {
  // ---- Status ----
  tmOnlineState:   { nodeid: 'ns=1;i=123457',    description: '在线状态',     unit: '',    value: 1,     precision: 0, amplitude: 0,    tone: 'emerald' },
  tmVendor:        { nodeid: 'ns=1;i=123458',    description: '控制器类别',   unit: '',    value: 1,     precision: 0, amplitude: 0,    tone: 'cyan' },
  tmAlarmState:    { nodeid: 'ns=1;i=1117790',   description: '警报状态',     unit: '',    value: 0,     precision: 0, amplitude: 0,    tone: 'amber' },
  tmOperateMode:   { nodeid: 'ns=1;i=1117792',   description: '操作模式',     unit: '',    value: 3,     precision: 0, amplitude: 0,    tone: 'cyan' },
  tmMotorState:    { nodeid: 'ns=1;i=1117789',   description: '马达状态',     unit: '',    value: 1,     precision: 0, amplitude: 0,    tone: 'emerald' },
  tmHeatState:     { nodeid: 'ns=1;i=1117788',   description: '电热状态',     unit: '',    value: 1,     precision: 0, amplitude: 0,    tone: 'emerald' },

  // ---- Production ----
  tmShotCount:     { nodeid: 'ns=1;i=1117188',   description: '开模次数',     unit: '次',  value: 38004, precision: 0, amplitude: 0,    tone: 'amber' },
  tmBadShotCount:  { nodeid: 'ns=1;i=1117190',   description: '不良品数',     unit: '次',  value: 120,   precision: 0, amplitude: 0,    tone: 'amber' },
  tmInferior:      { nodeid: 'ns=1;i=1117191',   description: '次品数',       unit: '个',  value: 45,    precision: 0, amplitude: 0,    tone: 'amber' },
  tmMoldCavity:    { nodeid: 'ns=1;i=1125380',   description: '模穴数',       unit: '穴',  value: 1,     precision: 0, amplitude: 0,    tone: 'violet' },

  // ---- Energy ----
  tmTotalEnergyConsumption:   { nodeid: 'ns=1;i=1117238', description: '总能耗',       unit: 'kWh', value: 1856.5, precision: 1, amplitude: 0.8,  tone: 'amber' },
  tmPowerConsumption:         { nodeid: 'ns=1;i=1117290', description: '当前功耗',     unit: 'kW',  value: 3.2,    precision: 1, amplitude: 0.3,  tone: 'amber' },
  tmPowerConsumptionRatio:    { nodeid: 'ns=1;i=1117301', description: '能耗系数',     unit: '',    value: 0.85,   precision: 2, amplitude: 0.02, tone: 'cyan' },
  tmPowerConsumptionPerModule:{ nodeid: 'ns=1;i=1117326', description: '每模能耗',     unit: 'kWh', value: 0.048,  precision: 3, amplitude: 0.003,tone: 'cyan' },

  // ---- Timings ----
  tmCycleTime:   { nodeid: 'ns=1;i=1114738', description: '循环时间', unit: '秒', value: 9.55,  precision: 2, amplitude: 0.3,  tone: 'cyan' },
  tmClpClsTime:  { nodeid: 'ns=1;i=1114739', description: '关模时间', unit: '秒', value: 1.76,  precision: 2, amplitude: 0.08, tone: 'violet' },
  tmInjTime:     { nodeid: 'ns=1;i=1114740', description: '射出时间', unit: '秒', value: 0.86,  precision: 2, amplitude: 0.05, tone: 'cyan' },
  tmTurnTime:    { nodeid: 'ns=1;i=1114741', description: '转保压时间',unit: '秒', value: 0.76, precision: 2, amplitude: 0.04, tone: 'violet' },
  tmChargeTime:  { nodeid: 'ns=1;i=1114742', description: '储料时间', unit: '秒', value: 2.23,  precision: 2, amplitude: 0.1,  tone: 'emerald' },
  tmClpOpnTime:  { nodeid: 'ns=1;i=1114743', description: '开模时间', unit: '秒', value: 1.40,  precision: 2, amplitude: 0.06, tone: 'amber' },
  tmInjBackTime: { nodeid: 'ns=1;i=1114744', description: '射退时间', unit: '秒', value: 0.30,  precision: 2, amplitude: 0.02, tone: 'cyan' },
  tmFetchTime:   { nodeid: 'ns=1;i=1114746', description: '取件时间', unit: '秒', value: 2.24,  precision: 2, amplitude: 0.15, tone: 'violet' },
  tmCoolingTime: { nodeid: 'ns=1;i=17900097', description: '冷却时间', unit: '秒', value: 3.0,  precision: 1, amplitude: 0.1,  tone: 'emerald' },

  // ---- Positions (measured) ----
  tmClpOpnPosi:   { nodeid: 'ns=1;i=1114747', description: '开模位置',     unit: 'mm', value: 257.0,  precision: 1, amplitude: 0.5, tone: 'emerald' },
  tmInjStartPosi: { nodeid: 'ns=1;i=1115208', description: '射出起点',     unit: 'mm', value: 106.5,  precision: 1, amplitude: 0.3, tone: 'cyan' },
  tmInjEndPosi:   { nodeid: 'ns=1;i=1115209', description: '射出终点',     unit: 'mm', value: 50.0,   precision: 1, amplitude: 0.2, tone: 'violet' },
  tmTurnPosi:     { nodeid: 'ns=1;i=1115210', description: '转保压位置',   unit: 'mm', value: 50.0,   precision: 1, amplitude: 0.2, tone: 'amber' },
  tmInjMoni:      { nodeid: 'ns=1;i=1115211', description: '射出监控',     unit: 'mm', value: 48.7,   precision: 1, amplitude: 0.3, tone: 'emerald' },

  // ---- Temperature current ----
  tmTemp1_Current: { nodeid: 'ns=1;i=135334536', description: '实际温度1', unit: '\u00B0C', value: 225.0, precision: 1, amplitude: 1.5, tone: 'amber' },
  tmTemp2_Current: { nodeid: 'ns=1;i=135334537', description: '实际温度2', unit: '\u00B0C', value: 256.0, precision: 1, amplitude: 1.2, tone: 'amber' },
  tmTemp3_Current: { nodeid: 'ns=1;i=135334538', description: '实际温度3', unit: '\u00B0C', value: 256.0, precision: 1, amplitude: 1.2, tone: 'cyan' },
  tmTemp4_Current: { nodeid: 'ns=1;i=135334539', description: '实际温度4', unit: '\u00B0C', value: 198.0, precision: 1, amplitude: 1.0, tone: 'cyan' },
  tmTemp5_Current: { nodeid: 'ns=1;i=135334540', description: '实际温度5', unit: '\u00B0C', value: 180.0, precision: 1, amplitude: 0.8, tone: 'violet' },
  tmTempOil_Current:{ nodeid: 'ns=1;i=135334897', description: '油温',     unit: '\u00B0C', value: 51.0,  precision: 1, amplitude: 0.5, tone: 'emerald' },

  // ---- Temperature set ----
  tmTemp1_Set: { nodeid: 'ns=1;i=135342608', description: '设定温度1', unit: '\u00B0C', value: 225.0, precision: 0, amplitude: 0, tone: 'amber' },
  tmTemp2_Set: { nodeid: 'ns=1;i=135342609', description: '设定温度2', unit: '\u00B0C', value: 255.0, precision: 0, amplitude: 0, tone: 'amber' },
  tmTemp3_Set: { nodeid: 'ns=1;i=135342610', description: '设定温度3', unit: '\u00B0C', value: 255.0, precision: 0, amplitude: 0, tone: 'cyan' },
  tmTemp4_Set: { nodeid: 'ns=1;i=135342611', description: '设定温度4', unit: '\u00B0C', value: 200.0, precision: 0, amplitude: 0, tone: 'cyan' },
  tmTemp5_Set: { nodeid: 'ns=1;i=135342612', description: '设定温度5', unit: '\u00B0C', value: 180.0, precision: 0, amplitude: 0, tone: 'violet' },
  tmTemp6_Set: { nodeid: 'ns=1;i=135342613', description: '设定温度6', unit: '\u00B0C', value: 0,     precision: 0, amplitude: 0, tone: 'violet' },
  tmTemp7_Set: { nodeid: 'ns=1;i=135342614', description: '设定温度7', unit: '\u00B0C', value: 0,     precision: 0, amplitude: 0, tone: 'emerald' },
  tmTemp8_Set: { nodeid: 'ns=1;i=135342615', description: '设定温度8', unit: '\u00B0C', value: 0,     precision: 0, amplitude: 0, tone: 'emerald' },
  tmTemp9_Set: { nodeid: 'ns=1;i=135342616', description: '设定温度9', unit: '\u00B0C', value: 0,     precision: 0, amplitude: 0, tone: 'amber' },

  // ---- Open mold (press / speed / position, 5 stages) ----
  tmClpOpnPress1: { nodeid: 'ns=1;i=16983592', description: '开模1段压力', unit: '%',  value: 66.0, precision: 1, amplitude: 0.3, tone: 'cyan' },
  tmClpOpnPress2: { nodeid: 'ns=1;i=16983593', description: '开模2段压力', unit: '%',  value: 50.0, precision: 1, amplitude: 0.2, tone: 'cyan' },
  tmClpOpnPress3: { nodeid: 'ns=1;i=16983594', description: '开模3段压力', unit: '%',  value: 50.0, precision: 1, amplitude: 0.2, tone: 'cyan' },
  tmClpOpnPress4: { nodeid: 'ns=1;i=16983595', description: '开模4段压力', unit: '%',  value: 20.0, precision: 1, amplitude: 0.1, tone: 'violet' },
  tmClpOpnPress5: { nodeid: 'ns=1;i=16983596', description: '开模5段压力', unit: '%',  value: 5.0,  precision: 1, amplitude: 0.05,tone: 'violet' },
  tmClpOpnSpeed1: { nodeid: 'ns=1;i=16982692', description: '开模1段速度', unit: '%',  value: 20.0, precision: 1, amplitude: 0.2, tone: 'violet' },
  tmClpOpnSpeed2: { nodeid: 'ns=1;i=16982693', description: '开模2段速度', unit: '%',  value: 50.0, precision: 1, amplitude: 0.3, tone: 'violet' },
  tmClpOpnSpeed3: { nodeid: 'ns=1;i=16982694', description: '开模3段速度', unit: '%',  value: 50.0, precision: 1, amplitude: 0.3, tone: 'violet' },
  tmClpOpnSpeed4: { nodeid: 'ns=1;i=16982695', description: '开模4段速度', unit: '%',  value: 15.0, precision: 1, amplitude: 0.1, tone: 'emerald' },
  tmClpOpnSpeed5: { nodeid: 'ns=1;i=16982696', description: '开模5段速度', unit: '%',  value: 10.0, precision: 1, amplitude: 0.1, tone: 'emerald' },
  tmClpOpnPosi1:  { nodeid: 'ns=1;i=16983092', description: '开模1段位置', unit: 'mm', value: 10.0, precision: 1, amplitude: 0.1, tone: 'emerald' },
  tmClpOpnPosi2:  { nodeid: 'ns=1;i=16983093', description: '开模2段位置', unit: 'mm', value: 50.0, precision: 1, amplitude: 0.2, tone: 'emerald' },
  tmClpOpnPosi3:  { nodeid: 'ns=1;i=16983094', description: '开模3段位置', unit: 'mm', value: 105.0,precision: 1, amplitude: 0.3, tone: 'amber' },
  tmClpOpnPosi4:  { nodeid: 'ns=1;i=16983095', description: '开模4段位置', unit: 'mm', value: 210.0,precision: 1, amplitude: 0.5, tone: 'amber' },
  tmClpOpnPosi5:  { nodeid: 'ns=1;i=16983096', description: '开模5段位置', unit: 'mm', value: 250.0,precision: 1, amplitude: 0.5, tone: 'amber' },

  // ---- Close mold (press / speed / position, 5+5+4 stages) ----
  tmClpClsPress1: { nodeid: 'ns=1;i=16918056', description: '关模1段压力', unit: '%',  value: 100.0, precision: 1, amplitude: 0.3, tone: 'cyan' },
  tmClpClsPress2: { nodeid: 'ns=1;i=16918057', description: '关模2段压力', unit: '%',  value: 140.0, precision: 1, amplitude: 0.4, tone: 'cyan' },
  tmClpClsPress3: { nodeid: 'ns=1;i=16918058', description: '关模3段压力', unit: '%',  value: 55.0,  precision: 1, amplitude: 0.2, tone: 'cyan' },
  tmClpClsPress4: { nodeid: 'ns=1;i=16918059', description: '关模4段压力', unit: '%',  value: 15.0,  precision: 1, amplitude: 0.1, tone: 'violet' },
  tmClpClsPress5: { nodeid: 'ns=1;i=16918060', description: '关模5段压力', unit: '%',  value: 120.0, precision: 1, amplitude: 0.3, tone: 'violet' },
  tmClpClsSpeed1: { nodeid: 'ns=1;i=16917156', description: '关模1段速度', unit: '%',  value: 65.0,  precision: 1, amplitude: 0.3, tone: 'violet' },
  tmClpClsSpeed2: { nodeid: 'ns=1;i=16917157', description: '关模2段速度', unit: '%',  value: 99.0,  precision: 1, amplitude: 0.3, tone: 'violet' },
  tmClpClsSpeed3: { nodeid: 'ns=1;i=16917158', description: '关模3段速度', unit: '%',  value: 88.0,  precision: 1, amplitude: 0.3, tone: 'violet' },
  tmClpClsSpeed4: { nodeid: 'ns=1;i=16917159', description: '关模4段速度', unit: '%',  value: 35.0,  precision: 1, amplitude: 0.2, tone: 'emerald' },
  tmClpClsSpeed5: { nodeid: 'ns=1;i=16917160', description: '关模5段速度', unit: '%',  value: 28.0,  precision: 1, amplitude: 0.2, tone: 'emerald' },
  tmClpClsPosi1:  { nodeid: 'ns=1;i=16917556', description: '关模1段位置', unit: 'mm', value: 248.0, precision: 1, amplitude: 0.3, tone: 'emerald' },
  tmClpClsPosi2:  { nodeid: 'ns=1;i=16917557', description: '关模2段位置', unit: 'mm', value: 60.0,  precision: 1, amplitude: 0.2, tone: 'emerald' },
  tmClpClsPosi3:  { nodeid: 'ns=1;i=16917558', description: '关模3段位置', unit: 'mm', value: 25.0,  precision: 1, amplitude: 0.1, tone: 'amber' },
  tmClpClsPosi4:  { nodeid: 'ns=1;i=16917559', description: '关模4段位置', unit: 'mm', value: 8.0,   precision: 1, amplitude: 0.05,tone: 'amber' },

  // ---- Injection (press / speed / position, 3 stages + extras) ----
  tmInjPress1:    { nodeid: 'ns=1;i=50603560', description: '射出1段压力', unit: '%',  value: 90.0, precision: 1, amplitude: 0.4, tone: 'cyan' },
  tmInjPress2:    { nodeid: 'ns=1;i=50603561', description: '射出2段压力', unit: '%',  value: 45.0, precision: 1, amplitude: 0.3, tone: 'cyan' },
  tmInjPress3:    { nodeid: 'ns=1;i=50603562', description: '射出3段压力', unit: '%',  value: 20.0, precision: 1, amplitude: 0.2, tone: 'cyan' },
  tmInjSpeed1:    { nodeid: 'ns=1;i=50602660', description: '射出1段速度', unit: '%',  value: 88.0, precision: 1, amplitude: 0.4, tone: 'violet' },
  tmInjSpeed2:    { nodeid: 'ns=1;i=50602661', description: '射出2段速度', unit: '%',  value: 43.0, precision: 1, amplitude: 0.3, tone: 'violet' },
  tmInjSpeed3:    { nodeid: 'ns=1;i=50602662', description: '射出3段速度', unit: '%',  value: 20.0, precision: 1, amplitude: 0.2, tone: 'violet' },
  tmInjPosi1:     { nodeid: 'ns=1;i=50603060', description: '射出1段位置', unit: 'mm', value: 62.5, precision: 1, amplitude: 0.2, tone: 'emerald' },
  tmInjPosi2:     { nodeid: 'ns=1;i=50603061', description: '射出2段位置', unit: 'mm', value: 15.0, precision: 1, amplitude: 0.1, tone: 'emerald' },
  tmInjBackPress: { nodeid: 'ns=1;i=50669096', description: '射退压力',   unit: '%',  value: 50.0, precision: 1, amplitude: 0.2, tone: 'amber' },
  tmInjBackSpeed: { nodeid: 'ns=1;i=50668196', description: '射退速度',   unit: '%',  value: 50.0, precision: 1, amplitude: 0.2, tone: 'amber' },
  tmInj2HoldPosn: { nodeid: 'ns=1;i=51127348', description: '射出转保压位置', unit: 'mm', value: 50.0, precision: 1, amplitude: 0.2, tone: 'cyan' },
  tmInj2HoldTime: { nodeid: 'ns=1;i=51126848', description: '射出转保压时间', unit: '秒', value: 0.92, precision: 2, amplitude: 0.03,tone: 'violet' },

  // ---- Charging (press / backpress / speed / position, 3 stages) ----
  tmChargePress1:     { nodeid: 'ns=1;i=68232744', description: '储料1段压力', unit: '%',  value: 99.0, precision: 1, amplitude: 0.3, tone: 'cyan' },
  tmChargePress2:     { nodeid: 'ns=1;i=68232745', description: '储料2段压力', unit: '%',  value: 99.0, precision: 1, amplitude: 0.3, tone: 'cyan' },
  tmChargePress3:     { nodeid: 'ns=1;i=68232746', description: '储料3段压力', unit: '%',  value: 99.0, precision: 1, amplitude: 0.3, tone: 'cyan' },
  tmChargeBackPress1: { nodeid: 'ns=1;i=68232844', description: '储料1段背压', unit: '%',  value: 4.0,  precision: 1, amplitude: 0.1, tone: 'violet' },
  tmChargeBackPress2: { nodeid: 'ns=1;i=68232845', description: '储料2段背压', unit: '%',  value: 4.0,  precision: 1, amplitude: 0.1, tone: 'violet' },
  tmChargeBackPress3: { nodeid: 'ns=1;i=68232846', description: '储料3段背压', unit: '%',  value: 4.0,  precision: 1, amplitude: 0.1, tone: 'violet' },
  tmChargeSpeed1:     { nodeid: 'ns=1;i=68231844', description: '储料1段速度', unit: '%',  value: 99.0, precision: 1, amplitude: 0.3, tone: 'emerald' },
  tmChargeSpeed2:     { nodeid: 'ns=1;i=68231845', description: '储料2段速度', unit: '%',  value: 99.0, precision: 1, amplitude: 0.3, tone: 'emerald' },
  tmChargeSpeed3:     { nodeid: 'ns=1;i=68231846', description: '储料3段速度', unit: '%',  value: 99.0, precision: 1, amplitude: 0.3, tone: 'emerald' },
  tmChargePosi1:      { nodeid: 'ns=1;i=68232244', description: '储料1段位置', unit: 'mm', value: 20.0, precision: 1, amplitude: 0.1, tone: 'amber' },
  tmChargePosi2:      { nodeid: 'ns=1;i=68232245', description: '储料2段位置', unit: 'mm', value: 90.0, precision: 1, amplitude: 0.2, tone: 'amber' },
  tmChargePosi3:      { nodeid: 'ns=1;i=68232246', description: '储料3段位置', unit: 'mm', value: 100.0,precision: 1, amplitude: 0.2, tone: 'amber' },

  // ---- Eject advance (2 stages) ----
  tmEjectAdvPress1:    { nodeid: 'ns=1;i=33826344', description: '托模进1段压力', unit: '%',  value: 50.0, precision: 1, amplitude: 0.2, tone: 'cyan' },
  tmEjectAdvPress2:    { nodeid: 'ns=1;i=33826345', description: '托模进2段压力', unit: '%',  value: 50.0, precision: 1, amplitude: 0.2, tone: 'cyan' },
  tmEjectAdvSpeed1:    { nodeid: 'ns=1;i=33825444', description: '托模进1段速度', unit: '%',  value: 30.0, precision: 1, amplitude: 0.2, tone: 'violet' },
  tmEjectAdvSpeed2:    { nodeid: 'ns=1;i=33825445', description: '托模进2段速度', unit: '%',  value: 50.0, precision: 1, amplitude: 0.2, tone: 'violet' },
  tmEjectAdvPosi1:     { nodeid: 'ns=1;i=33825844', description: '托模进1段位置', unit: 'mm', value: 10.0, precision: 1, amplitude: 0.1, tone: 'emerald' },
  tmEjectAdvPosi2:     { nodeid: 'ns=1;i=33825845', description: '托模进2段位置', unit: 'mm', value: 50.0, precision: 1, amplitude: 0.2, tone: 'emerald' },
  tmEjectAdvDelayTime: { nodeid: 'ns=1;i=33825344', description: '托模进延迟时间',unit: '秒', value: 0.01, precision: 2, amplitude: 0.002,tone: 'amber' },

  // ---- Eject retract (2 stages) ----
  tmEjectRetPress1:    { nodeid: 'ns=1;i=33891880', description: '托模退1段压力', unit: '%',  value: 60.0, precision: 1, amplitude: 0.2, tone: 'cyan' },
  tmEjectRetPress2:    { nodeid: 'ns=1;i=33891881', description: '托模退2段压力', unit: '%',  value: 60.0, precision: 1, amplitude: 0.2, tone: 'cyan' },
  tmEjectRetSpeed1:    { nodeid: 'ns=1;i=33890980', description: '托模退1段速度', unit: '%',  value: 60.0, precision: 1, amplitude: 0.2, tone: 'violet' },
  tmEjectRetSpeed2:    { nodeid: 'ns=1;i=33890981', description: '托模退2段速度', unit: '%',  value: 60.0, precision: 1, amplitude: 0.2, tone: 'violet' },
  tmEjectRetPosi1:     { nodeid: 'ns=1;i=33891380', description: '托模退1段位置', unit: 'mm', value: 10.0, precision: 1, amplitude: 0.1, tone: 'emerald' },
  tmEjectRetPosi2:     { nodeid: 'ns=1;i=33891381', description: '托模退2段位置', unit: 'mm', value: 1.0,  precision: 1, amplitude: 0.05,tone: 'emerald' },
  tmEjectRetDelayTime: { nodeid: 'ns=1;i=33890880', description: '托模退延迟时间',unit: '秒', value: 0.01, precision: 2, amplitude: 0.002,tone: 'amber' },

  // ---- Nozzle advance (2 stages) ----
  tmNozzleAdvPress1: { nodeid: 'ns=1;i=84157992', description: '座台进1段压力', unit: '%',  value: 99.0, precision: 1, amplitude: 0.3, tone: 'cyan' },
  tmNozzleAdvPress2: { nodeid: 'ns=1;i=84157993', description: '座台进2段压力', unit: '%',  value: 99.0, precision: 1, amplitude: 0.3, tone: 'cyan' },
  tmNozzleAdvSpeed1: { nodeid: 'ns=1;i=84157092', description: '座台进1段速度', unit: '%',  value: 40.0, precision: 1, amplitude: 0.2, tone: 'violet' },
  tmNozzleAdvSpeed2: { nodeid: 'ns=1;i=84157093', description: '座台进2段速度', unit: '%',  value: 40.0, precision: 1, amplitude: 0.2, tone: 'violet' },

  // ---- Nozzle retract ----
  tmNozzleRetPress1: { nodeid: 'ns=1;i=84223528', description: '座台退1段压力', unit: '%',  value: 50.0, precision: 1, amplitude: 0.2, tone: 'amber' },
  tmNozzleRetSpeed1: { nodeid: 'ns=1;i=84222628', description: '座台退1段速度', unit: '%',  value: 30.0, precision: 1, amplitude: 0.2, tone: 'amber' },
  tmNozzleRetPosi1:  { nodeid: 'ns=1;i=84223028', description: '座台退1段位置', unit: 'mm', value: 15.0, precision: 1, amplitude: 0.1, tone: 'emerald' },

  // ---- Core A/B/C in ----
  tmCoreAInPress: { nodeid: 'ns=1;i=151266856', description: '中子A进压力', unit: '%',  value: 60.0, precision: 1, amplitude: 0.2, tone: 'cyan' },
  tmCoreBInPress: { nodeid: 'ns=1;i=151266857', description: '中子B进压力', unit: '%',  value: 60.0, precision: 1, amplitude: 0.2, tone: 'cyan' },
  tmCoreCInPress: { nodeid: 'ns=1;i=151266858', description: '中子C进压力', unit: '%',  value: 60.0, precision: 1, amplitude: 0.2, tone: 'cyan' },
  tmCoreAInSpeed: { nodeid: 'ns=1;i=151265956', description: '中子A进速度', unit: '%',  value: 30.0, precision: 1, amplitude: 0.2, tone: 'violet' },
  tmCoreBInSpeed: { nodeid: 'ns=1;i=151265957', description: '中子B进速度', unit: '%',  value: 30.0, precision: 1, amplitude: 0.2, tone: 'violet' },
  tmCoreCInSpeed: { nodeid: 'ns=1;i=151265958', description: '中子C进速度', unit: '%',  value: 30.0, precision: 1, amplitude: 0.2, tone: 'violet' },
  tmCoreAInTime:  { nodeid: 'ns=1;i=151265856', description: '中子A进时间', unit: '秒', value: 1.5,  precision: 2, amplitude: 0.05,tone: 'emerald' },
  tmCoreBInTime:  { nodeid: 'ns=1;i=151265857', description: '中子B进时间', unit: '秒', value: 1.5,  precision: 2, amplitude: 0.05,tone: 'emerald' },
  tmCoreCInTime:  { nodeid: 'ns=1;i=151265858', description: '中子C进时间', unit: '秒', value: 1.5,  precision: 2, amplitude: 0.05,tone: 'emerald' },

  // ---- Core A/B/C out ----
  tmCoreAOutPress: { nodeid: 'ns=1;i=151332392', description: '中子A退压力', unit: '%',  value: 50.0, precision: 1, amplitude: 0.2, tone: 'amber' },
  tmCoreBOutPress: { nodeid: 'ns=1;i=151332393', description: '中子B退压力', unit: '%',  value: 50.0, precision: 1, amplitude: 0.2, tone: 'amber' },
  tmCoreCOutPress: { nodeid: 'ns=1;i=151332394', description: '中子C退压力', unit: '%',  value: 50.0, precision: 1, amplitude: 0.2, tone: 'amber' },
  tmCoreAOutSpeed: { nodeid: 'ns=1;i=151331492', description: '中子A退速度', unit: '%',  value: 25.0, precision: 1, amplitude: 0.2, tone: 'cyan' },
  tmCoreBOutSpeed: { nodeid: 'ns=1;i=151331493', description: '中子B退速度', unit: '%',  value: 25.0, precision: 1, amplitude: 0.2, tone: 'cyan' },
  tmCoreCOutSpeed: { nodeid: 'ns=1;i=151331494', description: '中子C退速度', unit: '%',  value: 25.0, precision: 1, amplitude: 0.2, tone: 'cyan' },
  tmCoreAOutTime:  { nodeid: 'ns=1;i=151331392', description: '中子A退时间', unit: '秒', value: 1.2,  precision: 2, amplitude: 0.04,tone: 'violet' },
  tmCoreBOutTime:  { nodeid: 'ns=1;i=151331393', description: '中子B退时间', unit: '秒', value: 1.2,  precision: 2, amplitude: 0.04,tone: 'violet' },
  tmCoreCOutTime:  { nodeid: 'ns=1;i=151331394', description: '中子C退时间', unit: '秒', value: 1.2,  precision: 2, amplitude: 0.04,tone: 'violet' },

  // ---- Clamp move ----
  tmClpMoveOption:  { nodeid: 'ns=1;i=17902596', description: '移模方式',     unit: '',   value: 1.0,  precision: 0, amplitude: 0,   tone: 'cyan' },
  tmClpMoveLPress:  { nodeid: 'ns=1;i=17049129', description: '左移模压力',   unit: '%',  value: 45.0, precision: 1, amplitude: 0.2, tone: 'cyan' },
  tmClpMoveLSPress: { nodeid: 'ns=1;i=17049130', description: '左移模慢速压力',unit: '%', value: 20.0, precision: 1, amplitude: 0.1, tone: 'violet' },
  tmClpMoveLSpeed:  { nodeid: 'ns=1;i=17048228', description: '左移模速度',   unit: '%',  value: 30.0, precision: 1, amplitude: 0.2, tone: 'violet' },
  tmLocatorPress:   { nodeid: 'ns=1;i=17573417', description: '定位压力',     unit: '%',  value: 35.0, precision: 1, amplitude: 0.2, tone: 'amber' },
};

// ---------------------------------------------------------------------------
// Page definitions
// ---------------------------------------------------------------------------

export interface PageDef {
  id: string;
  title: string;
  heroFields: Array<{ fieldId: string; label?: string }>;
  leftPanels: Array<{ title: string; fields: string[] }>;
  rightPanels: Array<{ title: string; fields: string[] }>;
  leftPie?: { title: string };
  leftTrend?: {
    title: string;
    series: TrendSeriesConfig[];
    trendFields: string[];
  };
  rightPie?: { title: string };
  showAlerts?: boolean;
}

export interface ParameterSectionDef {
  title: string;
  fields: string[];
  columns?: 2 | 3;
}

export const PAGE_DEFS: PageDef[] = [
  {
    id: 'overview',
    title: '设备总览',
    heroFields: [
      { fieldId: 'tmCycleTime', label: '循环时间' },
      { fieldId: 'tmShotCount', label: '当前模次' },
      { fieldId: 'tmOperateMode', label: '操作模式' },
    ],
    leftPanels: [
      {
        title: '生产统计',
        fields: [
          'tmShotCount', 'tmBadShotCount', 'tmInferior', 'tmMoldCavity',
        ],
      },
    ],
    rightPanels: [
      {
        title: '设备状态',
        fields: [
          'tmOnlineState', 'tmOperateMode', 'tmMotorState', 'tmHeatState',
          'tmPowerConsumption', 'tmPowerConsumptionRatio',
        ],
      },
    ],
    leftTrend: {
      title: '循环时间趋势',
      series: [
        { name: '循环时间', key: 'tmCycleTime', type: 'line', color: '#2fb6ff', areaColor: 'rgba(47,182,255,0.12)' },
        { name: '射出时间', key: 'tmInjTime', type: 'line', color: '#8be7ff' },
        { name: '储料时间', key: 'tmChargeTime', type: 'bar', color: 'rgba(52,120,246,0.58)', yAxisIndex: 1 },
      ],
      trendFields: ['tmCycleTime', 'tmInjTime', 'tmChargeTime'],
    },
    leftPie: { title: '产品质量分布' },
    rightPie: { title: '工时分布' },
    showAlerts: true,
  },
  {
    id: 'mold',
    title: '开关模参数',
    heroFields: [
      { fieldId: 'tmClpOpnTime', label: '开模时间' },
      { fieldId: 'tmClpClsTime', label: '关模时间' },
      { fieldId: 'tmClpOpnPosi', label: '开模位置' },
    ],
    leftPanels: [
      {
        title: '开关模摘要',
        fields: ['tmClpOpnTime', 'tmClpClsTime', 'tmClpOpnPosi', 'tmLocatorPress'],
      },
    ],
    rightPanels: [
      {
        title: '移模参数',
        fields: ['tmClpMoveOption', 'tmClpMoveLPress', 'tmClpMoveLSPress', 'tmClpMoveLSpeed', 'tmLocatorPress'],
      },
    ],
    showAlerts: true,
  },
  {
    id: 'injection',
    title: '射出与储料',
    heroFields: [
      { fieldId: 'tmInjTime', label: '射出时间' },
      { fieldId: 'tmChargeTime', label: '储料时间' },
      { fieldId: 'tmTurnTime', label: '转保压时间' },
    ],
    leftPanels: [
      {
        title: '位置与时间',
        fields: [
          'tmInjStartPosi', 'tmInjEndPosi', 'tmTurnPosi', 'tmInjMoni',
          'tmInjTime', 'tmTurnTime', 'tmInjBackTime', 'tmFetchTime',
        ],
      },
    ],
    rightPanels: [
      {
        title: '储料摘要',
        fields: ['tmChargeTime', 'tmInj2HoldTime', 'tmInjBackPress', 'tmInjBackSpeed'],
      },
    ],
    showAlerts: true,
  },
  {
    id: 'auxiliary',
    title: '辅助参数',
    heroFields: [
      { fieldId: 'tmCoolingTime', label: '冷却时间' },
      { fieldId: 'tmFetchTime', label: '取件时间' },
      { fieldId: 'tmTempOil_Current', label: '油温' },
    ],
    leftPanels: [
      {
        title: '托模进参数',
        fields: [
          'tmEjectAdvPress1', 'tmEjectAdvPress2',
          'tmEjectAdvSpeed1', 'tmEjectAdvSpeed2',
          'tmEjectAdvPosi1', 'tmEjectAdvPosi2',
          'tmEjectAdvDelayTime',
        ],
      },
      {
        title: '托模退参数',
        fields: [
          'tmEjectRetPress1', 'tmEjectRetPress2',
          'tmEjectRetSpeed1', 'tmEjectRetSpeed2',
          'tmEjectRetPosi1', 'tmEjectRetPosi2',
          'tmEjectRetDelayTime',
        ],
      },
    ],
    rightPanels: [
      {
        title: '座台参数',
        fields: [
          'tmNozzleAdvPress1', 'tmNozzleAdvPress2',
          'tmNozzleAdvSpeed1', 'tmNozzleAdvSpeed2',
          'tmNozzleRetPress1', 'tmNozzleRetSpeed1', 'tmNozzleRetPosi1',
        ],
      },
    ],
    showAlerts: true,
  },
  {
    id: 'all-params',
    title: '全量参数',
    heroFields: [
      { fieldId: 'tmShotCount', label: '当前模次' },
      { fieldId: 'tmCycleTime', label: '循环时间' },
      { fieldId: 'tmTotalEnergyConsumption', label: '总能耗' },
    ],
    leftPanels: [],
    rightPanels: [],
    showAlerts: false,
  },
];

export const ALL_PARAMETER_SECTIONS: {
  left: ParameterSectionDef[];
  center: ParameterSectionDef[];
  right: ParameterSectionDef[];
} = {
  left: [
    {
      title: '状态与产量',
      fields: [
        'tmOnlineState', 'tmAlarmState', 'tmOperateMode', 'tmMotorState', 'tmHeatState',
        'tmVendor', 'tmShotCount', 'tmBadShotCount', 'tmInferior', 'tmMoldCavity',
      ],
      columns: 2,
    },
    {
      title: '节拍与能耗',
      fields: [
        'tmCycleTime', 'tmClpClsTime', 'tmInjTime', 'tmTurnTime', 'tmChargeTime',
        'tmClpOpnTime', 'tmInjBackTime', 'tmFetchTime', 'tmCoolingTime',
        'tmTotalEnergyConsumption', 'tmPowerConsumption', 'tmPowerConsumptionRatio', 'tmPowerConsumptionPerModule',
      ],
      columns: 2,
    },
    {
      title: '当前与设定温度',
      fields: [
        'tmTemp1_Current', 'tmTemp2_Current', 'tmTemp3_Current',
        'tmTemp4_Current', 'tmTemp5_Current', 'tmTempOil_Current',
        'tmTemp1_Set', 'tmTemp2_Set', 'tmTemp3_Set',
        'tmTemp4_Set', 'tmTemp5_Set', 'tmTemp6_Set',
        'tmTemp7_Set', 'tmTemp8_Set', 'tmTemp9_Set',
      ],
      columns: 2,
    },
  ],
  center: [
    {
      title: '开模压力速度',
      fields: [
        'tmClpOpnPress1', 'tmClpOpnPress2', 'tmClpOpnPress3', 'tmClpOpnPress4', 'tmClpOpnPress5',
        'tmClpOpnSpeed1', 'tmClpOpnSpeed2', 'tmClpOpnSpeed3', 'tmClpOpnSpeed4', 'tmClpOpnSpeed5',
      ],
      columns: 3,
    },
    {
      title: '开模位置',
      fields: [
        'tmClpOpnPosi1', 'tmClpOpnPosi2', 'tmClpOpnPosi3', 'tmClpOpnPosi4', 'tmClpOpnPosi5',
      ],
      columns: 3,
    },
    {
      title: '关模压力速度',
      fields: [
        'tmClpClsPress1', 'tmClpClsPress2', 'tmClpClsPress3', 'tmClpClsPress4', 'tmClpClsPress5',
        'tmClpClsSpeed1', 'tmClpClsSpeed2', 'tmClpClsSpeed3', 'tmClpClsSpeed4', 'tmClpClsSpeed5',
      ],
      columns: 3,
    },
    {
      title: '关模位置',
      fields: [
        'tmClpClsPosi1', 'tmClpClsPosi2', 'tmClpClsPosi3', 'tmClpClsPosi4',
      ],
      columns: 3,
    },
    {
      title: '座台参数',
      fields: [
        'tmNozzleAdvPress1', 'tmNozzleAdvPress2',
        'tmNozzleAdvSpeed1', 'tmNozzleAdvSpeed2',
        'tmNozzleRetPress1', 'tmNozzleRetSpeed1', 'tmNozzleRetPosi1',
      ],
      columns: 3,
    },
    {
      title: '中子进参数',
      fields: [
        'tmCoreAInPress', 'tmCoreBInPress', 'tmCoreCInPress',
        'tmCoreAInSpeed', 'tmCoreBInSpeed', 'tmCoreCInSpeed',
        'tmCoreAInTime', 'tmCoreBInTime', 'tmCoreCInTime',
      ],
      columns: 3,
    },
  ],
  right: [
    {
      title: '射出压力速度',
      fields: [
        'tmInjPress1', 'tmInjPress2', 'tmInjPress3',
        'tmInjSpeed1', 'tmInjSpeed2', 'tmInjSpeed3',
      ],
      columns: 2,
    },
    {
      title: '射出位置与转换',
      fields: [
        'tmInjPosi1', 'tmInjPosi2', 'tmInjBackPress', 'tmInjBackSpeed',
        'tmInj2HoldPosn', 'tmInj2HoldTime', 'tmInjStartPosi', 'tmInjEndPosi', 'tmTurnPosi', 'tmInjMoni',
      ],
      columns: 2,
    },
    {
      title: '储料参数',
      fields: [
        'tmChargePress1', 'tmChargePress2', 'tmChargePress3',
        'tmChargeBackPress1', 'tmChargeBackPress2', 'tmChargeBackPress3',
        'tmChargeSpeed1', 'tmChargeSpeed2', 'tmChargeSpeed3',
        'tmChargePosi1', 'tmChargePosi2', 'tmChargePosi3',
      ],
      columns: 2,
    },
    {
      title: '托模进退参数',
      fields: [
        'tmEjectAdvPress1', 'tmEjectAdvPress2', 'tmEjectAdvSpeed1', 'tmEjectAdvSpeed2',
        'tmEjectAdvPosi1', 'tmEjectAdvPosi2', 'tmEjectAdvDelayTime',
        'tmEjectRetPress1', 'tmEjectRetPress2', 'tmEjectRetSpeed1', 'tmEjectRetSpeed2',
        'tmEjectRetPosi1', 'tmEjectRetPosi2', 'tmEjectRetDelayTime',
      ],
      columns: 2,
    },
    {
      title: '中子退参数',
      fields: [
        'tmCoreAOutPress', 'tmCoreBOutPress', 'tmCoreCOutPress',
        'tmCoreAOutSpeed', 'tmCoreBOutSpeed', 'tmCoreCOutSpeed',
        'tmCoreAOutTime', 'tmCoreBOutTime', 'tmCoreCOutTime',
      ],
      columns: 2,
    },
  ],
};

// ---------------------------------------------------------------------------
// State & helpers
// ---------------------------------------------------------------------------

export interface RealtimeState {
  device_name: string;
  shot_count: number;
  timestamp: string;
  fields: Record<string, number>;
  prevFields: Record<string, number>;
  trends: TrendPoint[];
  events: EventRecord[];
  healthScore: number;
}

const FIELD_VALUE_LABELS: Record<string, Record<number, string>> = {
  tmOnlineState: { 0: '离线', 1: '在线' },
  tmAlarmState: { 0: '正常', 1: '告警' },
  tmOperateMode: { 1: '手动', 2: '半自动', 3: '全自动' },
  tmMotorState: { 0: '停止', 1: '运行' },
  tmHeatState: { 0: '关闭', 1: '开启' },
};

const randomBetween = (min: number, max: number) => min + Math.random() * (max - min);
const clamp = (v: number, lo: number, hi: number) => Math.min(hi, Math.max(lo, v));

export function getFieldDef(id: string) {
  return FIELD_DEFS[id];
}

export function formatFieldValue(fieldId: string, value: number): string {
  const def = FIELD_DEFS[fieldId];
  if (!def) return String(value);
  const label = FIELD_VALUE_LABELS[fieldId]?.[value];
  if (label) return label;
  return value.toFixed(def.precision);
}

export function formatHeroValue(fieldId: string, value: number): string {
  const def = FIELD_DEFS[fieldId];
  if (!def) return String(value);
  const displayValue = formatFieldValue(fieldId, value);
  if (FIELD_VALUE_LABELS[fieldId]?.[value]) return displayValue;
  return `${displayValue} ${def.unit}`.trim();
}

export function fieldsToMetrics(
  fields: Record<string, number>,
  prevFields: Record<string, number>,
  fieldIds: string[],
): MetricCard[] {
  return fieldIds.map((id) => {
    const def = FIELD_DEFS[id];
    if (!def) return { id, title: id, unit: '', value: 0, delta: 0, tone: 'cyan' as MetricTone };
    const value = fields[id] ?? def.value;
    const prev = prevFields[id] ?? def.value;
    const delta = prev !== 0 ? ((value - prev) / Math.abs(prev)) * 100 : 0;
    return {
      id,
      title: def.description,
      unit: def.unit,
      value,
      precision: def.precision,
      delta: Number(delta.toFixed(1)),
      tone: def.tone,
    };
  });
}

export function getQualityPieData(fields: Record<string, number>) {
  const total = fields.tmShotCount ?? 0;
  const bad = fields.tmInferior ?? 0;
  return [
    { name: '良品', value: Math.max(total - bad, 0) },
    { name: '次品', value: bad },
  ];
}

export function getTimePieData(fields: Record<string, number>) {
  return [
    { name: '关模', value: Number((fields.tmClpClsTime ?? 0).toFixed(2)) },
    { name: '射出', value: Number((fields.tmInjTime ?? 0).toFixed(2)) },
    { name: '保压', value: Number((fields.tmTurnTime ?? 0).toFixed(2)) },
    { name: '储料', value: Number((fields.tmChargeTime ?? 0).toFixed(2)) },
    { name: '开模', value: Number((fields.tmClpOpnTime ?? 0).toFixed(2)) },
    { name: '冷却', value: Number((fields.tmCoolingTime ?? 0).toFixed(2)) },
  ];
}

function buildInitialFields(): Record<string, number> {
  const result: Record<string, number> = {};
  for (const [key, def] of Object.entries(FIELD_DEFS)) {
    result[key] = def.value;
  }
  return result;
}

function buildInitialTrends(fields: Record<string, number>): TrendPoint[] {
  const points: TrendPoint[] = [];
  for (let i = -5; i <= 0; i++) {
    const shot = (fields.tmShotCount ?? 38004) + i;
    const values: Record<string, number> = {};
    for (const key of Object.keys(FIELD_DEFS)) {
      const def = FIELD_DEFS[key];
      values[key] = def.value + randomBetween(-def.amplitude, def.amplitude);
    }
    values.tmShotCount = shot;
    points.push({ label: `#${shot}`, values });
  }
  return points;
}

const eventTitles = [
  '温度波动提醒',
  '循环时间异常',
  '压力参数变化',
  '储料速度偏差',
  '设备状态更新',
  '模具冷却正常',
  '注射参数稳定',
];

const eventDescs = [
  '检测到温度区间略有波动，系统已自动记录。',
  '当前循环时间在正常范围内，持续监控中。',
  '射出压力轻微浮动，未超出设定阈值。',
  '储料参数已完成同步，各段数据正常。',
  '模具冷却温度稳定，油温在设定范围内。',
  '开关模参数已同步至最新生产周期。',
  '托模与座台参数正常，无异常报警。',
];

function buildInitialEvents(): EventRecord[] {
  const now = new Date();
  return [
    {
      id: 'evt-init-1',
      level: 'info',
      title: '系统启动完成',
      description: '注塑机监控系统已就绪，开始接收实时数据。',
      timestamp: `${String(now.getHours()).padStart(2, '0')}:${String(now.getMinutes()).padStart(2, '0')}:${String(now.getSeconds()).padStart(2, '0')}`,
    },
    {
      id: 'evt-init-2',
      level: 'warning',
      title: '油温偏高提醒',
      description: '油温接近设定上限，建议关注冷却系统。',
      timestamp: `${String(now.getHours()).padStart(2, '0')}:${String(Math.max(now.getMinutes() - 1, 0)).padStart(2, '0')}:00`,
    },
    {
      id: 'evt-init-3',
      level: 'info',
      title: '生产数据同步',
      description: '已完成最近一次模次数据采集和同步。',
      timestamp: `${String(now.getHours()).padStart(2, '0')}:${String(Math.max(now.getMinutes() - 2, 0)).padStart(2, '0')}:30`,
    },
  ];
}

export function createInitialRealtimeState(): RealtimeState {
  const fields = buildInitialFields();
  return {
    device_name: 'ZS-001',
    shot_count: fields.tmShotCount,
    timestamp: new Date().toISOString(),
    fields,
    prevFields: { ...fields },
    trends: buildInitialTrends(fields),
    events: buildInitialEvents(),
    healthScore: 96.4,
  };
}

export function evolveRealtimeState(prev: RealtimeState): RealtimeState {
  const prevFields = { ...prev.fields };
  const fields: Record<string, number> = {};

  for (const [key, def] of Object.entries(FIELD_DEFS)) {
    const old = prev.fields[key] ?? def.value;
    if (def.amplitude === 0) {
      fields[key] = old;
    } else {
      fields[key] = Number(
        clamp(old + randomBetween(-def.amplitude, def.amplitude), Math.max(0, old - def.amplitude * 8), old + def.amplitude * 8).toFixed(
          def.precision,
        ),
      );
    }
  }

  fields.tmShotCount = prev.fields.tmShotCount + 1;
  fields.tmTotalEnergyConsumption = Number(
    (prev.fields.tmTotalEnergyConsumption + randomBetween(0.03, 0.06)).toFixed(1),
  );
  if (Math.random() < 0.03) {
    fields.tmInferior = prev.fields.tmInferior + 1;
    fields.tmBadShotCount = prev.fields.tmBadShotCount + 1;
  } else {
    fields.tmInferior = prev.fields.tmInferior;
    fields.tmBadShotCount = prev.fields.tmBadShotCount;
  }

  const trendValues: Record<string, number> = {};
  for (const key of Object.keys(fields)) {
    trendValues[key] = fields[key];
  }

  const newTrend: TrendPoint = {
    label: `#${fields.tmShotCount}`,
    values: trendValues,
  };
  const trends = [...prev.trends.slice(-5), newTrend];

  const now = new Date();
  const ts = `${String(now.getHours()).padStart(2, '0')}:${String(now.getMinutes()).padStart(2, '0')}:${String(now.getSeconds()).padStart(2, '0')}`;

  const newEvent: EventRecord = {
    id: `evt-${Date.now()}`,
    level: (['info', 'warning', 'info', 'info', 'critical'] as const)[Math.floor(Math.random() * 5)],
    title: eventTitles[Math.floor(Math.random() * eventTitles.length)],
    description: eventDescs[Math.floor(Math.random() * eventDescs.length)],
    timestamp: ts,
  };

  return {
    device_name: prev.device_name,
    shot_count: fields.tmShotCount,
    timestamp: now.toISOString(),
    fields,
    prevFields,
    trends,
    events: [newEvent, ...prev.events].slice(0, 6),
    healthScore: Number(clamp(prev.healthScore + randomBetween(-0.5, 0.5), 90, 99.8).toFixed(1)),
  };
}
