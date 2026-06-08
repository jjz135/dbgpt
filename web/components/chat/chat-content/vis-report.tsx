import { AutoChart, BackEndChartType, getChartType } from '@/components/chart';
import { Datum } from '@antv/ava';
import { GPTVis } from '@antv/gpt-vis';
import { useMemo } from 'react';
import remarkGfm from 'remark-gfm';
import markdownComponents from './config';

// Generic section type that can be text or chart
interface ReportSection {
  type: 'text' | 'chart';
  title?: string;
  content?: string;  // For text sections
  chart_type?: BackEndChartType;  // For chart sections
  sql?: string;
  description?: string;
  data?: Datum[];
  err_msg?: string;
  [key: string]: any;  // Allow additional fields from LLM
}

interface Props {
  data: {
    title: string;
    summary: string;
    sections: ReportSection[];
    section_count?: number;
    display_strategy?: string;
    style?: string;
  };
}

function VisReport({ data }: Props) {
  const { title, summary, sections } = data;

  const renderedSections = useMemo(() => {
    return sections.map((section, index) => {
      if (section.type === 'text') {
        // Render text section
        return (
          <div key={`section-${index}`} className="mb-6">
            {section.title && (
              <h3 className="text-lg font-semibold mb-3 text-gray-800 dark:text-gray-200 border-l-4 border-blue-500 pl-3">
                {section.title}
              </h3>
            )}
            <div className="prose prose-sm dark:prose-invert max-w-none text-gray-700 dark:text-gray-300 leading-relaxed">
              <GPTVis components={markdownComponents} remarkPlugins={[remarkGfm]}>
                {section.content || ''}
              </GPTVis>
            </div>
          </div>
        );
      } else if (section.type === 'chart') {
        // Render chart section
        return (
          <div 
            key={`section-${index}`} 
            className="mb-6 p-4 rounded-lg border border-gray-200 dark:border-gray-600 bg-white dark:bg-gray-800 shadow-sm"
          >
            {section.title && (
              <h3 className="text-lg font-semibold mb-2 text-gray-800 dark:text-gray-200">
                {section.title}
              </h3>
            )}
            {section.description && (
              <p className="mb-4 text-sm text-gray-600 dark:text-gray-400 leading-relaxed">
                {section.description}
              </p>
            )}
            {section.err_msg ? (
              <div className="p-4 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded text-red-600 dark:text-red-400 text-sm">
                <strong>查询错误: </strong>{section.err_msg}
              </div>
            ) : section.data && section.data.length > 0 ? (
              <div className="min-h-[300px]">
                <AutoChart 
                  data={section.data} 
                  chartType={getChartType(section.chart_type)} 
                />
              </div>
            ) : (
              <div className="p-4 bg-gray-50 dark:bg-gray-700 rounded text-gray-500 dark:text-gray-400 text-center">
                暂无数据
              </div>
            )}
          </div>
        );
      }
      return null;
    });
  }, [sections]);

  return (
    <div className="vis-report bg-gray-50 dark:bg-gray-900 rounded-xl p-6 shadow-md">
      {/* Report Header */}
      <div className="mb-6 pb-4 border-b-2 border-blue-500">
        <h1 className="text-2xl font-bold text-gray-900 dark:text-white mb-3">
          📊 {title}
        </h1>
        {summary && (
          <div className="bg-blue-50 dark:bg-blue-900/30 border-l-4 border-blue-500 p-4 rounded-r-lg">
            <p className="text-sm font-medium text-gray-500 dark:text-gray-400 mb-1">
              执行摘要
            </p>
            <p className="text-gray-700 dark:text-gray-300 leading-relaxed">
              {summary}
            </p>
          </div>
        )}
      </div>

      {/* Report Sections */}
      <div className="report-content">
        {renderedSections}
      </div>

      {/* Report Footer */}
      <div className="mt-6 pt-4 border-t border-gray-200 dark:border-gray-700">
        <p className="text-xs text-gray-400 dark:text-gray-500 text-center">
          报告由 AI 自动生成 · 共 {sections.length} 个分析模块
        </p>
      </div>
    </div>
  );
}

export default VisReport;

