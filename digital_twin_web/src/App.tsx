import { Progress, Tag } from 'antd';
import type { ReactNode } from 'react';
import { useCallback, useEffect, useMemo, useRef, useState } from 'react';

import AgentChatPanel from '@/components/chat/AgentChatPanel';
import { DIGITAL_TWIN_MODEL_URL } from '@/config/runtime';
import ScreenFrame from '@/components/layout/ScreenFrame';
import ModelStage from '@/components/model/ModelStage';
import BarChartPanel from '@/components/panels/BarChartPanel';
import MetricPanel from '@/components/panels/MetricPanel';
import ParameterPanel from '@/components/panels/ParameterPanel';
import PieChartPanel from '@/components/panels/PieChartPanel';
import RadarChartPanel from '@/components/panels/RadarChartPanel';
import TrendPanel from '@/components/panels/TrendPanel';
import {
  ALL_PARAMETER_SECTIONS,
  PAGE_DEFS,
  createInitialRealtimeState,
  evolveRealtimeState,
  fieldsToMetrics,
  formatHeroValue,
  getQualityPieData,
  getTimePieData,
} from '@/mock/realtime';

const modelUrl = DIGITAL_TWIN_MODEL_URL;
const getValue = (fields: Record<string, number>, fieldId: string) => Number(fields[fieldId] ?? 0);

function App() {
  const [realtimeState, setRealtimeState] = useState(createInitialRealtimeState);
  const [currentPageId, setCurrentPageId] = useState(PAGE_DEFS[0].id);
  const [activeAppName, setActiveAppName] = useState<string>();
  const [isChatExpanded, setIsChatExpanded] = useState(false);
  const chatWrapRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (chatWrapRef.current && !chatWrapRef.current.contains(event.target as Node)) {
        setIsChatExpanded(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  useEffect(() => {
    const timer = window.setInterval(() => {
      setRealtimeState((current) => evolveRealtimeState(current));
    }, 3200);
    return () => window.clearInterval(timer);
  }, []);

  const handleActiveAppChange = useCallback((name: string) => {
    setActiveAppName(name);
  }, []);

  const currentPage = PAGE_DEFS.find((p) => p.id === currentPageId) ?? PAGE_DEFS[0];
  const isAllParamsPage = currentPageId === 'all-params';
  const { fields, prevFields, trends, events, healthScore } = realtimeState;
  const leftPanels = useMemo(
    () =>
      currentPage.leftPanels.map((panel) => ({
        ...panel,
        metrics: fieldsToMetrics(fields, prevFields, panel.fields),
      })),
    [currentPage.leftPanels, fields, prevFields],
  );
  const rightPanels = useMemo(
    () =>
      currentPage.rightPanels.map((panel) => ({
        ...panel,
        metrics: fieldsToMetrics(fields, prevFields, panel.fields),
      })),
    [currentPage.rightPanels, fields, prevFields],
  );
  const allParamPanels = useMemo(
    () => ({
      left: ALL_PARAMETER_SECTIONS.left.map((section) => ({
        ...section,
        metrics: fieldsToMetrics(fields, prevFields, section.fields),
      })),
      center: ALL_PARAMETER_SECTIONS.center.map((section) => ({
        ...section,
        metrics: fieldsToMetrics(fields, prevFields, section.fields),
      })),
      right: ALL_PARAMETER_SECTIONS.right.map((section) => ({
        ...section,
        metrics: fieldsToMetrics(fields, prevFields, section.fields),
      })),
    }),
    [fields, prevFields],
  );
  const { leftVisualPanels, rightVisualPanels } = useMemo(() => {
    const left: ReactNode[] = [];
    const right: ReactNode[] = [];

    if (currentPageId === 'overview') {
      left.push(
        <BarChartPanel
          key='overview-cycle'
          title='节拍构成'
          className='panel-card--chart-medium'
          categories={['循环', '冷却', '射出', '储料', '开模', '关模']}
          series={[
            {
              name: '时间',
              data: [
                getValue(fields, 'tmCycleTime'),
                getValue(fields, 'tmCoolingTime'),
                getValue(fields, 'tmInjTime'),
                getValue(fields, 'tmChargeTime'),
                getValue(fields, 'tmClpOpnTime'),
                getValue(fields, 'tmClpClsTime'),
              ],
              color: '#2fb6ff',
            },
          ]}
        />,
      );
      right.push(
        <BarChartPanel
          key='overview-temp'
          title='温区温度对比'
          className='panel-card--chart-medium'
          categories={['1区', '2区', '3区', '4区', '5区']}
          series={[
            {
              name: '设定温度',
              data: ['tmTemp1_Set', 'tmTemp2_Set', 'tmTemp3_Set', 'tmTemp4_Set', 'tmTemp5_Set'].map((id) => getValue(fields, id)),
              color: '#3478f6',
            },
            {
              name: '当前温度',
              data: ['tmTemp1_Current', 'tmTemp2_Current', 'tmTemp3_Current', 'tmTemp4_Current', 'tmTemp5_Current'].map((id) =>
                getValue(fields, id),
              ),
              color: '#ffb347',
            },
          ]}
        />,
      );
    }

    if (currentPageId === 'mold') {
      left.push(
        <BarChartPanel
          key='mold-open-speed'
          title='开模压力速度'
          className='panel-card--chart-medium'
          categories={['1段', '2段', '3段', '4段', '5段']}
          series={[
            {
              name: '开模压力',
              data: ['tmClpOpnPress1', 'tmClpOpnPress2', 'tmClpOpnPress3', 'tmClpOpnPress4', 'tmClpOpnPress5'].map((id) =>
                getValue(fields, id),
              ),
              color: '#2fb6ff',
            },
            {
              name: '开模速度',
              data: ['tmClpOpnSpeed1', 'tmClpOpnSpeed2', 'tmClpOpnSpeed3', 'tmClpOpnSpeed4', 'tmClpOpnSpeed5'].map((id) =>
                getValue(fields, id),
              ),
              color: '#8be7ff',
            },
          ]}
        />,
      );
      left.push(
        <BarChartPanel
          key='mold-open-position'
          title='开模位置分布'
          className='panel-card--chart-medium'
          categories={['1段', '2段', '3段', '4段', '5段']}
          series={[
            {
              name: '开模位置',
              data: ['tmClpOpnPosi1', 'tmClpOpnPosi2', 'tmClpOpnPosi3', 'tmClpOpnPosi4', 'tmClpOpnPosi5'].map((id) =>
                getValue(fields, id),
              ),
              color: '#2fb6ff',
            },
            {
              name: '开模压力',
              data: ['tmClpOpnPress1', 'tmClpOpnPress2', 'tmClpOpnPress3', 'tmClpOpnPress4', 'tmClpOpnPress5'].map((id) =>
                getValue(fields, id),
              ),
              color: '#8be7ff',
              type: 'line',
            },
          ]}
        />,
      );
      right.push(
        <BarChartPanel
          key='mold-close-speed'
          title='关模压力速度'
          className='panel-card--chart-medium'
          categories={['1段', '2段', '3段', '4段', '5段']}
          series={[
            {
              name: '关模压力',
              data: ['tmClpClsPress1', 'tmClpClsPress2', 'tmClpClsPress3', 'tmClpClsPress4', 'tmClpClsPress5'].map((id) =>
                getValue(fields, id),
              ),
              color: '#3478f6',
            },
            {
              name: '关模速度',
              data: ['tmClpClsSpeed1', 'tmClpClsSpeed2', 'tmClpClsSpeed3', 'tmClpClsSpeed4', 'tmClpClsSpeed5'].map((id) =>
                getValue(fields, id),
              ),
              color: '#ffb347',
            },
          ]}
        />,
      );
      right.push(
        <BarChartPanel
          key='mold-close-position'
          title='关模位置分布'
          className='panel-card--chart-medium'
          categories={['1段', '2段', '3段', '4段']}
          series={[
            {
              name: '关模位置',
              data: ['tmClpClsPosi1', 'tmClpClsPosi2', 'tmClpClsPosi3', 'tmClpClsPosi4'].map((id) => getValue(fields, id)),
              color: '#7c94ff',
            },
          ]}
        />,
      );
    }

    if (currentPageId === 'injection') {
      left.push(
        <BarChartPanel
          key='inj-stage'
          title='射出阶段分布'
          className='panel-card--chart-medium'
          categories={['1段', '2段', '转保']}
          series={[
            {
              name: '射出压力',
              data: ['tmInjPress1', 'tmInjPress2', 'tmInjPress3'].map((id) => getValue(fields, id)),
              color: '#2fb6ff',
            },
            {
              name: '射出速度',
              data: ['tmInjSpeed1', 'tmInjSpeed2', 'tmInjSpeed3'].map((id) => getValue(fields, id)),
              color: '#7c94ff',
            },
            {
              name: '位置转换',
              data: ['tmInjPosi1', 'tmInjPosi2', 'tmInj2HoldPosn'].map((id) => getValue(fields, id)),
              color: '#8be7ff',
              type: 'line',
            },
          ]}
        />,
      );
      const injectionMax = Math.max(
        120,
        getValue(fields, 'tmInjStartPosi'),
        getValue(fields, 'tmInjEndPosi'),
        getValue(fields, 'tmTurnPosi'),
        getValue(fields, 'tmInjMoni'),
      );
      left.push(
        <RadarChartPanel
          key='inj-position-radar'
          title='射出位置特征'
          className='panel-card--chart-medium'
          indicators={[
            { name: '射出起点', max: injectionMax },
            { name: '射出终点', max: injectionMax },
            { name: '转保位置', max: injectionMax },
            { name: '射出监控', max: injectionMax },
          ]}
          series={[
            {
              name: '当前位置特征',
              value: [
                getValue(fields, 'tmInjStartPosi'),
                getValue(fields, 'tmInjEndPosi'),
                getValue(fields, 'tmTurnPosi'),
                getValue(fields, 'tmInjMoni'),
              ],
              color: '#2fb6ff',
            },
          ]}
        />,
      );
      right.push(
        <BarChartPanel
          key='charge-stage'
          title='储料阶段分布'
          className='panel-card--chart-medium'
          categories={['1段', '2段', '3段']}
          series={[
            {
              name: '储料压力',
              data: ['tmChargePress1', 'tmChargePress2', 'tmChargePress3'].map((id) => getValue(fields, id)),
              color: '#2fb6ff',
            },
            {
              name: '储料速度',
              data: ['tmChargeSpeed1', 'tmChargeSpeed2', 'tmChargeSpeed3'].map((id) => getValue(fields, id)),
              color: '#48d597',
            },
            {
              name: '储料位置',
              data: ['tmChargePosi1', 'tmChargePosi2', 'tmChargePosi3'].map((id) => getValue(fields, id)),
              color: '#8be7ff',
              type: 'line',
            },
          ]}
        />,
      );
      const chargeMax = Math.max(
        100,
        ...['tmChargePress1', 'tmChargePress2', 'tmChargePress3'].map((id) => getValue(fields, id)),
        ...['tmChargeBackPress1', 'tmChargeBackPress2', 'tmChargeBackPress3'].map((id) => getValue(fields, id)),
      );
      right.push(
        <RadarChartPanel
          key='charge-back-pressure'
          title='储料压力背压对比'
          className='panel-card--chart-medium'
          indicators={[
            { name: '1段', max: chargeMax },
            { name: '2段', max: chargeMax },
            { name: '3段', max: chargeMax },
          ]}
          series={[
            {
              name: '储料压力',
              value: ['tmChargePress1', 'tmChargePress2', 'tmChargePress3'].map((id) => getValue(fields, id)),
              color: '#2fb6ff',
            },
            {
              name: '储料背压',
              value: ['tmChargeBackPress1', 'tmChargeBackPress2', 'tmChargeBackPress3'].map((id) => getValue(fields, id)),
              color: '#48d597',
            },
          ]}
        />,
      );
    }

    if (currentPageId === 'auxiliary') {
      left.push(
        <BarChartPanel
          key='temp-compare'
          title='温区设定对比'
          className='panel-card--chart-medium'
          categories={['1区', '2区', '3区', '4区', '5区']}
          series={[
            {
              name: '设定温度',
              data: ['tmTemp1_Set', 'tmTemp2_Set', 'tmTemp3_Set', 'tmTemp4_Set', 'tmTemp5_Set'].map((id) => getValue(fields, id)),
              color: '#3478f6',
            },
            {
              name: '当前温度',
              data: ['tmTemp1_Current', 'tmTemp2_Current', 'tmTemp3_Current', 'tmTemp4_Current', 'tmTemp5_Current'].map((id) =>
                getValue(fields, id),
              ),
              color: '#ffb347',
            },
          ]}
        />,
      );
      const coreInPress = ['tmCoreAInPress', 'tmCoreBInPress', 'tmCoreCInPress'].map((id) => getValue(fields, id));
      const coreOutPress = ['tmCoreAOutPress', 'tmCoreBOutPress', 'tmCoreCOutPress'].map((id) => getValue(fields, id));
      const radarMax = Math.max(100, ...coreInPress, ...coreOutPress);
      right.push(
        <RadarChartPanel
          key='core-radar'
          title='中子压力对比'
          className='panel-card--chart-medium'
          indicators={[
            { name: '中子A', max: radarMax },
            { name: '中子B', max: radarMax },
            { name: '中子C', max: radarMax },
          ]}
          series={[
            { name: '进压力', value: coreInPress, color: '#2fb6ff' },
            { name: '退压力', value: coreOutPress, color: '#48d597' },
          ]}
        />,
      );
      right.push(
        <BarChartPanel
          key='nozzle-motion'
          title='座台动作对比'
          className='panel-card--chart-medium'
          categories={['进1段', '进2段', '退1段']}
          series={[
            {
              name: '压力',
              data: ['tmNozzleAdvPress1', 'tmNozzleAdvPress2', 'tmNozzleRetPress1'].map((id) => getValue(fields, id)),
              color: '#3478f6',
            },
            {
              name: '速度',
              data: ['tmNozzleAdvSpeed1', 'tmNozzleAdvSpeed2', 'tmNozzleRetSpeed1'].map((id) => getValue(fields, id)),
              color: '#ffb347',
            },
          ]}
        />,
      );
    }

    return { leftVisualPanels: left, rightVisualPanels: right };
  }, [currentPageId, fields]);

  return (
    <ScreenFrame
      pages={PAGE_DEFS}
      currentPageId={currentPageId}
      onPageChange={setCurrentPageId}
      deviceName={realtimeState.device_name}
      shotCount={realtimeState.shot_count}
      onlineStatus={fields.tmOnlineState ?? 1}
      activeAppName={activeAppName}
    >
      <main className='screen-main'>
        <div className='screen-main__top'>
          {/* ---- LEFT SIDEBAR ---- */}
          <aside className='screen-main__aside screen-main__aside--left'>
            {isAllParamsPage
              ? allParamPanels.left.map((panel) => (
                  <ParameterPanel
                    key={panel.title}
                    title={panel.title}
                    metrics={panel.metrics}
                    columns={panel.columns}
                  />
                ))
              : (
                  <>
                    {leftPanels.map((panel) => (
                      <MetricPanel
                        key={panel.title}
                        title={panel.title}
                        metrics={panel.metrics}
                      />
                    ))}

                    {currentPage.leftPie && (
                      <PieChartPanel
                        title={currentPage.leftPie.title}
                        data={getQualityPieData(fields)}
                        colors={['#2fb6ff', '#ff5959']}
                      />
                    )}

                    {currentPage.leftTrend && (
                      <TrendPanel
                        title={currentPage.leftTrend.title}
                        trends={trends}
                        seriesConfig={currentPage.leftTrend.series}
                      />
                    )}

                    {leftVisualPanels}
                  </>
                )}
          </aside>

          {/* ---- CENTER ---- */}
          <section
            className={`screen-main__center ${isAllParamsPage ? 'screen-main__center--all-params' : ''}`}
            style={{ paddingBottom: isAllParamsPage ? 0 : isChatExpanded ? 660 : 300 }}
          >
            {!isAllParamsPage && (
              <div className='hero-stats'>
                {currentPage.heroFields.map((hero) => (
                  <div key={hero.fieldId} className='hero-stat'>
                    <span>{hero.label ?? hero.fieldId}</span>
                    <strong>{formatHeroValue(hero.fieldId, fields[hero.fieldId] ?? 0)}</strong>
                  </div>
                ))}
              </div>
            )}
            {isAllParamsPage ? (
              <div className='all-params-center'>
                {allParamPanels.center.map((panel) => (
                  <ParameterPanel
                    key={panel.title}
                    title={panel.title}
                    metrics={panel.metrics}
                    columns={panel.columns}
                  />
                ))}
              </div>
            ) : (
              <>
                <ModelStage modelUrl={modelUrl} />
                <div
                  ref={chatWrapRef}
                  className={`screen-main__chat-wrap ${isChatExpanded ? 'is-expanded' : ''}`}
                  onClick={() => {
                    if (!isChatExpanded) setIsChatExpanded(true);
                  }}
                >
                  <AgentChatPanel activeAppName={activeAppName} onActiveAppChange={handleActiveAppChange} />
                </div>
              </>
            )}
          </section>

          {/* ---- RIGHT SIDEBAR ---- */}
          <aside className='screen-main__aside screen-main__aside--right'>
            {isAllParamsPage
              ? allParamPanels.right.map((panel) => (
                  <ParameterPanel
                    key={panel.title}
                    title={panel.title}
                    metrics={panel.metrics}
                    columns={panel.columns}
                  />
                ))
              : (
                  <>
                    {rightPanels.map((panel) => (
                      <MetricPanel
                        key={panel.title}
                        title={panel.title}
                        metrics={panel.metrics}
                      />
                    ))}

                    {currentPage.rightPie && (
                      <PieChartPanel
                        title={currentPage.rightPie.title}
                        data={getTimePieData(fields)}
                        className='panel-card--chart-compact'
                      />
                    )}

                    {rightVisualPanels}
                  </>
                )}

            {!isAllParamsPage && currentPage.showAlerts !== false && (
              <section className='panel-card panel-card--compact panel-card--alerts'>
                <div className='panel-card__heading'>
                  <span className='panel-card__line' />
                  <h3>告警与状态</h3>
                </div>
                <div className='tag-cloud'>
                  <Tag color='blue'>OPC 数据采集</Tag>
                  <Tag color='cyan'>实时监控</Tag>
                  <Tag color='purple'>参数追踪</Tag>
                  <Tag color='geekblue'>异常检测</Tag>
                </div>
                <div className='health-progress'>
                  <span>设备健康度</span>
                  <Progress percent={healthScore} strokeColor='#3fb9ff' trailColor='rgba(255,255,255,0.08)' />
                </div>
                <div className='monitor-event-list'>
                  {events.slice(0, 2).map((event) => (
                    <div key={event.id} className={`monitor-event monitor-event--${event.level}`}>
                      <div className='monitor-event__title'>
                        <span>{event.title}</span>
                        <time>{event.timestamp}</time>
                      </div>
                      <p>{event.description}</p>
                    </div>
                  ))}
                </div>
              </section>
            )}
          </aside>
        </div>
      </main>
    </ScreenFrame>
  );
}

export default App;
